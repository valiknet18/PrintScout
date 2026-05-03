from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._likes_helpers import fetch_like_counts
from app.api.auth import current_user
from app.core.db import get_session
from app.models import CachedModel, Like, User

router = APIRouter(prefix="/api/likes", tags=["likes"])


class LikeBody(BaseModel):
    source: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=128)


class LikedHit(BaseModel):
    source: str
    source_id: str
    title: str
    url: str
    thumbnail_url: str | None
    is_free: bool
    tags: list[str]
    like_count: int


class LikedListResponse(BaseModel):
    items: list[LikedHit]


class LikeIdPair(BaseModel):
    source: str
    source_id: str


class LikeToggleResponse(BaseModel):
    source: str
    source_id: str
    liked: bool
    like_count: int


@router.get("/ids", response_model=list[LikeIdPair])
async def liked_ids(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[LikeIdPair]:
    """Compact list of (source, source_id) the current user has liked.

    Frontend uses this once to populate a Set used for the heart state on
    every card without per-card requests.
    """
    rows = await session.execute(
        select(CachedModel.source, CachedModel.source_id)
        .join(Like, Like.cached_model_id == CachedModel.id)
        .where(Like.user_id == user.id)
    )
    return [LikeIdPair(source=s, source_id=sid) for s, sid in rows.all()]


@router.get("", response_model=LikedListResponse)
async def list_my_likes(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> LikedListResponse:
    rows = await session.execute(
        select(CachedModel)
        .join(Like, Like.cached_model_id == CachedModel.id)
        .where(Like.user_id == user.id)
        .order_by(desc(Like.created_at))
        .limit(limit)
    )
    models = list(rows.scalars())
    counts = await fetch_like_counts(
        session, [(m.source, m.source_id) for m in models]
    )
    return LikedListResponse(
        items=[
            LikedHit(
                source=m.source,
                source_id=m.source_id,
                title=m.title,
                url=m.url,
                thumbnail_url=m.thumbnail_url,
                is_free=m.is_free,
                tags=m.tags or [],
                like_count=counts.get((m.source, m.source_id), 0),
            )
            for m in models
        ]
    )


async def _resolve_cached_model(
    session: AsyncSession, source: str, source_id: str
) -> CachedModel:
    res = await session.execute(
        select(CachedModel).where(
            CachedModel.source == source, CachedModel.source_id == source_id
        )
    )
    model = res.scalar_one_or_none()
    if model is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "model not in cache (search for it first to populate)",
        )
    return model


async def _global_like_count(session: AsyncSession, cached_model_id: int) -> int:
    res = await session.execute(
        select(func.count(Like.id)).where(Like.cached_model_id == cached_model_id)
    )
    return int(res.scalar_one() or 0)


@router.post("", response_model=LikeToggleResponse, status_code=status.HTTP_201_CREATED)
async def like(
    body: LikeBody,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> LikeToggleResponse:
    model = await _resolve_cached_model(session, body.source, body.source_id)

    existing = await session.execute(
        select(Like).where(
            Like.user_id == user.id, Like.cached_model_id == model.id
        )
    )
    if existing.scalar_one_or_none() is None:
        session.add(Like(user_id=user.id, cached_model_id=model.id))
        await session.commit()

    return LikeToggleResponse(
        source=model.source,
        source_id=model.source_id,
        liked=True,
        like_count=await _global_like_count(session, model.id),
    )


@router.delete(
    "/{source}/{source_id}",
    response_model=LikeToggleResponse,
)
async def unlike(
    source: Annotated[str, Path(min_length=1, max_length=32)],
    source_id: Annotated[str, Path(min_length=1, max_length=128)],
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> LikeToggleResponse:
    model = await _resolve_cached_model(session, source, source_id)
    res = await session.execute(
        select(Like).where(
            Like.user_id == user.id, Like.cached_model_id == model.id
        )
    )
    like_row = res.scalar_one_or_none()
    if like_row is not None:
        await session.delete(like_row)
        await session.commit()

    return LikeToggleResponse(
        source=model.source,
        source_id=model.source_id,
        liked=False,
        like_count=await _global_like_count(session, model.id),
    )
