import asyncio
import hashlib
import logging
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.cache import get_redis
from app.core.db import get_session
from app.models import CachedModel, Printer, User
from app.sources.base import ModelStub, SourceAdapter
from app.sources.registry import enabled_sources
from app.translation import translate_to_english

router = APIRouter(prefix="/api", tags=["search"])

log = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 60 * 60  # 1h


class SearchHit(BaseModel):
    source: str
    source_id: str
    title: str
    url: str
    thumbnail_url: str | None
    is_free: bool
    tags: list[str]


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[SearchHit]
    # When the user's query was translated, `query` holds what was actually
    # sent to source APIs and `original_query` holds what the user typed.
    query: str | None = None
    original_query: str | None = None


def _cache_key(source: str, q: str, paid: str, nozzle: float | None, page: int) -> str:
    raw = f"{source}|{q.lower().strip()}|{paid}|{nozzle}|{page}"
    return "search:" + hashlib.sha1(raw.encode()).hexdigest()


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


async def _search_one_source(
    source: SourceAdapter,
    *,
    q: str,
    paid: str,
    page: int,
    per_source_size: int,
    nozzle: float | None,
) -> tuple[list[ModelStub], int]:
    cache_key = _cache_key(source.name, q, paid, nozzle, page)
    redis = get_redis()
    cached = await redis.get(cache_key)
    if cached:
        try:
            payload = SearchResponse.model_validate_json(cached)
            stubs = [
                ModelStub(
                    source=h.source,
                    source_id=h.source_id,
                    title=h.title,
                    url=h.url,
                    thumbnail_url=h.thumbnail_url,
                    is_free=h.is_free,
                    tags=h.tags,
                )
                for h in payload.items
            ]
            return stubs, payload.total
        except Exception:
            log.exception("bad cache entry %s; refetching", cache_key)

    try:
        items, total = await source.search(
            q,
            page=page,
            page_size=per_source_size,
            paid=None if paid == "all" else paid,
            nozzle_mm=nozzle,
        )
    except Exception:
        log.exception("source %s failed; returning empty", source.name)
        return [], 0

    cache_payload = SearchResponse(
        total=total,
        page=page,
        page_size=per_source_size,
        items=[SearchHit(**{k: v for k, v in asdict(s).items() if k != "preview_stl_url"}) for s in items],
    )
    try:
        await redis.set(cache_key, cache_payload.model_dump_json(), ex=_CACHE_TTL_SECONDS)
    except Exception:
        log.exception("redis set failed; continuing")

    return items, total


def _interleave(per_source: list[list[ModelStub]]) -> list[ModelStub]:
    """Round-robin merge so users see variety from page 1, not all-source-A then all-source-B."""
    out: list[ModelStub] = []
    i = 0
    while True:
        progressed = False
        for lst in per_source:
            if i < len(lst):
                out.append(lst[i])
                progressed = True
        if not progressed:
            break
        i += 1
    return out


@router.get("/search", response_model=SearchResponse)
async def search(
    printer_id: Annotated[int, Query(ge=1)],
    q: Annotated[str, Query(min_length=1, max_length=120)],
    paid: Annotated[Literal["free", "paid", "all"], Query()] = "free",
    page: Annotated[int, Query(ge=1, le=50)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 30,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    result = await session.execute(
        select(Printer).where(Printer.id == printer_id, Printer.user_id == user.id)
    )
    printer = result.scalar_one_or_none()
    if printer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "printer not found")

    # We DON'T pre-filter at the source by printer.nozzle_mm. Most uploaders
    # leave nozzle metadata blank, so it cuts ~90% of relevant hits. The real
    # fit decision happens per-card via /api/check_fit (parses the actual STL).
    sources = enabled_sources()
    if not sources:
        return SearchResponse(
            total=0,
            page=page,
            page_size=page_size,
            items=[],
            query=q,
            original_query=None,
        )

    # Touch `printer` so unused-arg lints don't yell — kept around for future
    # source-specific filters.
    _ = printer

    # Translate non-English queries before hitting source catalogs.
    translated = await translate_to_english(q)
    search_q = translated or q

    # Per-source page size — divide budget but never go below 10 per source so
    # smaller-catalog sources still contribute.
    per_source_size = max(10, page_size // len(sources))

    results = await asyncio.gather(
        *(
            _search_one_source(
                src,
                q=search_q,
                paid=paid,
                page=page,
                per_source_size=per_source_size,
                nozzle=None,
            )
            for src in sources
        ),
        return_exceptions=False,
    )

    # Persist hits from every source.
    for items, _ in results:
        await _persist_hits(session, items)

    merged = _interleave([items for items, _ in results])[:page_size]
    total = sum(t for _, t in results)

    return SearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            SearchHit(**{k: v for k, v in asdict(h).items() if k != "preview_stl_url"})
            for h in merged
        ],
        query=search_q,
        original_query=q if translated else None,
    )
