"""Compute and cache bounding-box dimensions for source models.

A model's representative file is parsed once with `trimesh`; dimensions are
stored in `model_files` keyed by `(cached_model_id, file_id)` and never expire
(file contents are immutable per source_id).

The preview file URL may be eagerly captured at search time (e.g. Printables)
or lazily resolved here via the source's get_files() (e.g. Thingiverse).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matcher.fit import Bbox
from app.matcher.parse import FileTooLargeError, parse_bbox_from_url
from app.models import CachedModel, ModelFile
from app.sources.registry import get_source

log = logging.getLogger(__name__)

_PREVIEW_FILE_KEY = "preview"


async def get_or_compute_bbox(
    session: AsyncSession, *, source: str, source_id: str
) -> Bbox | None:
    """Return the bounding box for a model's representative file, computing on demand."""
    result = await session.execute(
        select(CachedModel).where(
            CachedModel.source == source, CachedModel.source_id == source_id
        )
    )
    cached = result.scalar_one_or_none()
    if cached is None:
        return None

    cached_bbox = await _load_cached_bbox(session, cached.id, _PREVIEW_FILE_KEY)
    if cached_bbox is not None:
        return cached_bbox

    file_url = await _resolve_preview_url(session, cached)
    if not file_url:
        return None

    try:
        bbox = await parse_bbox_from_url(file_url)
    except FileTooLargeError as e:
        log.info("skipping bbox parse: %s", e)
        return None
    except Exception:
        log.exception("failed to parse %s", file_url)
        return None

    if bbox is None:
        return None

    await _persist_bbox(
        session,
        cached_model_id=cached.id,
        file_id=_PREVIEW_FILE_KEY,
        file_url=file_url,
        bbox=bbox,
    )
    return bbox


async def _resolve_preview_url(
    session: AsyncSession, cached: CachedModel
) -> str | None:
    """Return a parseable file URL, fetching from the source on first miss."""
    raw_meta = cached.raw_meta or {}
    url = raw_meta.get("preview_stl_url")
    if url:
        return url

    source = get_source(cached.source)
    if source is None or not source.is_enabled:
        return None

    try:
        files = await source.get_files(cached.source_id)
    except Exception:
        log.exception("get_files failed for %s/%s", cached.source, cached.source_id)
        return None
    if not files:
        return None

    chosen = files[0]
    cached.raw_meta = {**raw_meta, "preview_stl_url": chosen.file_url}
    await session.commit()
    return chosen.file_url


async def _load_cached_bbox(
    session: AsyncSession, cached_model_id: int, file_id: str
) -> Bbox | None:
    result = await session.execute(
        select(ModelFile).where(
            ModelFile.cached_model_id == cached_model_id,
            ModelFile.file_id == file_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None or row.bbox_x_mm is None:
        return None
    return Bbox(x=row.bbox_x_mm, y=row.bbox_y_mm, z=row.bbox_z_mm)


async def _persist_bbox(
    session: AsyncSession,
    *,
    cached_model_id: int,
    file_id: str,
    file_url: str,
    bbox: Bbox,
) -> None:
    fmt = PurePosixPath(file_url).suffix.lstrip(".").lower() or "stl"
    row = ModelFile(
        cached_model_id=cached_model_id,
        file_id=file_id,
        file_url=file_url,
        fmt=fmt,
        bbox_x_mm=bbox.x,
        bbox_y_mm=bbox.y,
        bbox_z_mm=bbox.z,
        parsed_at=datetime.now(timezone.utc),
    )
    session.add(row)
    await session.commit()
