from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import current_user
from app.core.db import get_session
from app.models import CachedModel, Collection, CollectionItem, User

router = APIRouter(prefix="/api/collections", tags=["collections"])


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CollectionListItem(BaseModel):
    id: int
    name: str
    item_count: int
    cover_thumbnail_url: str | None


class CollectionItemOut(BaseModel):
    source: str
    source_id: str
    title: str
    url: str
    thumbnail_url: str | None
    is_free: bool
    tags: list[str]


class CollectionDetail(BaseModel):
    id: int
    name: str
    items: list[CollectionItemOut]


class AddItemBody(BaseModel):
    source: str = Field(min_length=1, max_length=32)
    source_id: str = Field(min_length=1, max_length=128)


async def _scoped_collection(
    session: AsyncSession, *, collection_id: int, user: User
) -> Collection:
    result = await session.execute(
        select(Collection).where(
            Collection.id == collection_id, Collection.user_id == user.id
        )
    )
    coll = result.scalar_one_or_none()
    if coll is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "collection not found")
    return coll


@router.get("/membership/{source}/{source_id}", response_model=list[int])
async def membership(
    source: Annotated[str, Path(min_length=1, max_length=32)],
    source_id: Annotated[str, Path(min_length=1, max_length=128)],
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[int]:
    """IDs of the user's collections that contain the given model."""
    rows = await session.execute(
        select(Collection.id)
        .join(CollectionItem, CollectionItem.collection_id == Collection.id)
        .join(CachedModel, CachedModel.id == CollectionItem.cached_model_id)
        .where(
            Collection.user_id == user.id,
            CachedModel.source == source,
            CachedModel.source_id == source_id,
        )
    )
    return [r[0] for r in rows.all()]


@router.get("", response_model=list[CollectionListItem])
async def list_collections(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CollectionListItem]:
    # One round-trip: collection + count + a single cover thumbnail (most-recent item).
    item_count_subq = (
        select(
            CollectionItem.collection_id,
            func.count(CollectionItem.id).label("c"),
        )
        .group_by(CollectionItem.collection_id)
        .subquery()
    )
    rows = await session.execute(
        select(Collection, func.coalesce(item_count_subq.c.c, 0))
        .outerjoin(item_count_subq, item_count_subq.c.collection_id == Collection.id)
        .where(Collection.user_id == user.id)
        .order_by(Collection.created_at.desc())
    )

    out: list[CollectionListItem] = []
    for coll, count in rows.all():
        cover = None
        if count:
            thumb_row = await session.execute(
                select(CachedModel.thumbnail_url)
                .join(
                    CollectionItem,
                    CollectionItem.cached_model_id == CachedModel.id,
                )
                .where(CollectionItem.collection_id == coll.id)
                .order_by(CollectionItem.added_at.desc())
                .limit(1)
            )
            cover = thumb_row.scalar_one_or_none()
        out.append(
            CollectionListItem(
                id=coll.id,
                name=coll.name,
                item_count=int(count),
                cover_thumbnail_url=cover,
            )
        )
    return out


@router.post(
    "", response_model=CollectionListItem, status_code=status.HTTP_201_CREATED
)
async def create_collection(
    payload: CollectionIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> CollectionListItem:
    coll = Collection(user_id=user.id, name=payload.name.strip())
    session.add(coll)
    await session.commit()
    await session.refresh(coll)
    return CollectionListItem(
        id=coll.id, name=coll.name, item_count=0, cover_thumbnail_url=None
    )


@router.get("/{collection_id}", response_model=CollectionDetail)
async def get_collection(
    collection_id: Annotated[int, Path(ge=1)],
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> CollectionDetail:
    result = await session.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == user.id)
        .options(selectinload(Collection.items).selectinload(CollectionItem.cached_model))
    )
    coll = result.scalar_one_or_none()
    if coll is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "collection not found")
    return CollectionDetail(
        id=coll.id,
        name=coll.name,
        items=[
            CollectionItemOut(
                source=it.cached_model.source,
                source_id=it.cached_model.source_id,
                title=it.cached_model.title,
                url=it.cached_model.url,
                thumbnail_url=it.cached_model.thumbnail_url,
                is_free=it.cached_model.is_free,
                tags=it.cached_model.tags or [],
            )
            for it in coll.items
        ],
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: Annotated[int, Path(ge=1)],
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    coll = await _scoped_collection(session, collection_id=collection_id, user=user)
    await session.delete(coll)
    await session.commit()


@router.post(
    "/{collection_id}/items",
    response_model=CollectionItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    collection_id: Annotated[int, Path(ge=1)],
    payload: AddItemBody,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> CollectionItemOut:
    coll = await _scoped_collection(session, collection_id=collection_id, user=user)

    cached = await session.execute(
        select(CachedModel).where(
            CachedModel.source == payload.source,
            CachedModel.source_id == payload.source_id,
        )
    )
    model = cached.scalar_one_or_none()
    if model is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "model not in cache (search for it first to populate)",
        )

    existing = await session.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == coll.id,
            CollectionItem.cached_model_id == model.id,
        )
    )
    if existing.scalar_one_or_none() is None:
        session.add(
            CollectionItem(collection_id=coll.id, cached_model_id=model.id)
        )
        await session.commit()

    return CollectionItemOut(
        source=model.source,
        source_id=model.source_id,
        title=model.title,
        url=model.url,
        thumbnail_url=model.thumbnail_url,
        is_free=model.is_free,
        tags=model.tags or [],
    )


@router.delete(
    "/{collection_id}/items/{source}/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_item(
    collection_id: Annotated[int, Path(ge=1)],
    source: Annotated[str, Path(min_length=1, max_length=32)],
    source_id: Annotated[str, Path(min_length=1, max_length=128)],
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    coll = await _scoped_collection(session, collection_id=collection_id, user=user)
    result = await session.execute(
        select(CollectionItem)
        .join(CachedModel, CachedModel.id == CollectionItem.cached_model_id)
        .where(
            CollectionItem.collection_id == coll.id,
            CachedModel.source == source,
            CachedModel.source_id == source_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return  # idempotent
    await session.delete(item)
    await session.commit()
