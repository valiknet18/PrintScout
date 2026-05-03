from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._likes_helpers import fetch_like_counts
from app.api.auth import current_user
from app.core.db import get_session
from app.models import CachedModel, User

router = APIRouter(prefix="/api", tags=["model"])


class BboxOut(BaseModel):
    x: float
    y: float
    z: float


class ModelFileOut(BaseModel):
    file_id: str
    file_url: str
    fmt: str
    bbox: BboxOut | None


class ModelDetailOut(BaseModel):
    source: str
    source_id: str
    title: str
    url: str
    thumbnail_url: str | None
    is_free: bool
    tags: list[str]
    files: list[ModelFileOut]
    like_count: int = 0


@router.get("/model/{source}/{source_id}", response_model=ModelDetailOut)
async def get_model(
    source: Annotated[str, Path(min_length=1, max_length=32)],
    source_id: Annotated[str, Path(min_length=1, max_length=128)],
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ModelDetailOut:
    result = await session.execute(
        select(CachedModel)
        .where(CachedModel.source == source, CachedModel.source_id == source_id)
        .options(selectinload(CachedModel.files))
    )
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "model not in cache")

    files = [
        ModelFileOut(
            file_id=f.file_id,
            file_url=f.file_url,
            fmt=f.fmt,
            bbox=BboxOut(x=f.bbox_x_mm, y=f.bbox_y_mm, z=f.bbox_z_mm)
            if f.bbox_x_mm is not None
            else None,
        )
        for f in model.files
    ]

    counts = await fetch_like_counts(session, [(model.source, model.source_id)])
    return ModelDetailOut(
        source=model.source,
        source_id=model.source_id,
        title=model.title,
        url=model.url,
        thumbnail_url=model.thumbnail_url,
        is_free=model.is_free,
        tags=model.tags or [],
        files=files,
        like_count=counts.get((model.source, model.source_id), 0),
    )
