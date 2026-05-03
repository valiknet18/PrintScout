"""Popular feed.

Order of preference:
  1. Models the community has actually liked, ordered by global like count
     descending.
  2. Backfill from each source's "popular" listing (currently Printables) so
     a fresh deployment with zero likes still has something to show on Home.

The combined payload is cached in-memory for ~6h so all users see the same
front page and we don't burn through Printables API budget on every Home open.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._likes_helpers import fetch_like_counts
from app.api.auth import current_user
from app.core.cache import get_redis
from app.core.db import get_session
from app.models import CachedModel, Like, User
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
    like_count: int = 0


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


async def _liked_models(
    session: AsyncSession, *, limit: int
) -> list[tuple[CachedModel, int]]:
    """Top-N most-liked models, with their global like counts. Skips models
    nobody has liked (count > 0)."""
    stmt = (
        select(CachedModel, func.count(Like.id).label("c"))
        .join(Like, Like.cached_model_id == CachedModel.id)
        .group_by(CachedModel.id)
        .order_by(desc("c"))
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [(m, int(c)) for m, c in rows.all()]


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

    # 1) Most-liked first.
    liked = await _liked_models(session, limit=limit)
    seen: set[tuple[str, str]] = {(m.source, m.source_id) for m, _ in liked}
    items: list[PopularItem] = [
        PopularItem(
            source=m.source,
            source_id=m.source_id,
            title=m.title,
            url=m.url,
            thumbnail_url=m.thumbnail_url,
            is_free=m.is_free,
            tags=m.tags or [],
            like_count=count,
        )
        for m, count in liked
    ]

    # 2) Fill remaining slots from each source's own popular feed, deduping.
    if len(items) < limit:
        sources = enabled_sources()
        if sources:
            results = await asyncio.gather(*(_fetch_one(src) for src in sources))
            backfill: list[ModelStub] = []
            i = 0
            while len(items) + len(backfill) < limit:
                progressed = False
                for lst in results:
                    if i < len(lst):
                        h = lst[i]
                        key_pair = (h.source, h.source_id)
                        if key_pair not in seen:
                            backfill.append(h)
                            seen.add(key_pair)
                        progressed = True
                if not progressed:
                    break
                i += 1
            await _persist_hits(session, backfill)

            counts = await fetch_like_counts(
                session, [(h.source, h.source_id) for h in backfill]
            )
            for h in backfill[: limit - len(items)]:
                items.append(
                    PopularItem(
                        **{
                            k: v
                            for k, v in asdict(h).items()
                            if k != "preview_stl_url"
                        },
                        like_count=counts.get((h.source, h.source_id), 0),
                    )
                )

    payload = PopularResponse(items=items[:limit])
    try:
        await redis.set(key, payload.model_dump_json(), ex=_CACHE_TTL_SECONDS)
    except Exception:
        log.exception("redis set failed; continuing")
    return payload
