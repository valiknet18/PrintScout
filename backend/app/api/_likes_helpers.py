"""Shared like-count helpers used by search/popular/model/collection endpoints."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CachedModel, Like


async def fetch_like_counts(
    session: AsyncSession, pairs: Iterable[tuple[str, str]]
) -> dict[tuple[str, str], int]:
    """Return {(source, source_id): like_count} for the given hits.

    One round-trip via tuple-IN. Pairs not in cached_models map to 0
    implicitly (caller defaults missing keys to 0).
    """
    pair_list = list({(s, sid) for s, sid in pairs})
    if not pair_list:
        return {}

    stmt = (
        select(
            CachedModel.source,
            CachedModel.source_id,
            func.count(Like.id),
        )
        .outerjoin(Like, Like.cached_model_id == CachedModel.id)
        .where(tuple_(CachedModel.source, CachedModel.source_id).in_(pair_list))
        .group_by(CachedModel.source, CachedModel.source_id)
    )
    rows = await session.execute(stmt)
    return {(s, sid): int(cnt) for s, sid, cnt in rows.all()}
