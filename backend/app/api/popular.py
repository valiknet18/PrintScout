"""Globally cached popular models — same payload for every user, regenerated every few hours."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.cache import get_redis
from app.core.db import get_session
from app.models import CachedModel, User
from app.sources.base import ModelStub
from app.sources.printables import PrintablesSource
from app.sources.registry import enabled_sources

router = APIRouter(prefix="/api", tags=["popular"])

log = logging.getLogger(__name__)
_CACHE_KEY_PREFIX = "popular:v1"
_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6h


class PopularItem(BaseModel):
    source: str
    source_id: str
    title: str
    url: str
    thumbnail_url: str | None
    is_free: bool
    tags: list[str]


class PopularResponse(BaseModel):
    items: list[PopularItem]


def _cache_key(limit: int) -> str:
    return f"{_CACHE_KEY_PREFIX}:{limit}"


async def _persist_hits(session: AsyncSession, hits: list[ModelStub]) -> None:
    if not hits:
        return
    rows = [
        {
            "source": h.source,
            "source_id": h.source_id,
            "title": h.title,
            "url": h.url,
            "thumbnail_url": h.thumbnail_url,
            "is_free": h.is_free,
            "tags": h.tags,
            "raw_meta": {"preview_stl_url": h.preview_stl_url} if h.preview_stl_url else {},
        }
        for h in hits
    ]
    stmt = pg_insert(CachedModel).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source", "source_id"],
        set_={
            "title": stmt.excluded.title,
            "url": stmt.excluded.url,
            "thumbnail_url": stmt.excluded.thumbnail_url,
            "is_free": stmt.excluded.is_free,
            "tags": stmt.excluded.tags,
            "raw_meta": stmt.excluded.raw_meta,
        },
    )
    await session.execute(stmt)
    await session.commit()


async def _fetch_one(src) -> list[ModelStub]:
    if not isinstance(src, PrintablesSource):
        # Other adapters don't expose a popular() method yet — phase 2.
        return []
    try:
        return await src.popular(limit=24)
    except Exception:
        log.exception("popular() failed for %s", src.name)
        return []


@router.get("/popular", response_model=PopularResponse)
async def popular(
    limit: Annotated[int, Query(ge=1, le=48)] = 24,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PopularResponse:
    redis = get_redis()
    key = _cache_key(limit)

    try:
        cached = await redis.get(key)
    except Exception:
        log.exception("redis get failed; refetching")
        cached = None
    if cached:
        return PopularResponse.model_validate_json(cached)

    sources = enabled_sources()
    if not sources:
        return PopularResponse(items=[])

    results = await asyncio.gather(*(_fetch_one(src) for src in sources))
    merged: list[ModelStub] = []
    # Round-robin so multi-source diversity shows on first load.
    i = 0
    while True:
        progressed = False
        for lst in results:
            if i < len(lst):
                merged.append(lst[i])
                progressed = True
        if not progressed:
            break
        i += 1
    merged = merged[:limit]

    await _persist_hits(session, merged)

    payload = PopularResponse(
        items=[
            PopularItem(**{k: v for k, v in asdict(h).items() if k != "preview_stl_url"})
            for h in merged
        ]
    )
    try:
        await redis.set(key, payload.model_dump_json(), ex=_CACHE_TTL_SECONDS)
    except Exception:
        log.exception("redis set failed; continuing")
    return payload
