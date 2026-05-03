from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.matcher.dimensions import get_or_compute_bbox
from app.matcher.fit import Bbox, BuildVolume, fits
from app.models import Printer, User

router = APIRouter(prefix="/api", tags=["fit"])


class BboxOut(BaseModel):
    x: float
    y: float
    z: float


class FitResponse(BaseModel):
    status: Literal["fits", "too_big", "unknown"]
    bbox: BboxOut | None
    margin_pct: float


@router.get("/check_fit", response_model=FitResponse)
async def check_fit(
    printer_id: Annotated[int, Query(ge=1)],
    source: Annotated[str, Query(min_length=1, max_length=32)],
    source_id: Annotated[str, Query(min_length=1, max_length=128)],
    margin_pct: Annotated[float, Query(ge=0, le=50)] = 5.0,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> FitResponse:
    result = await session.execute(
        select(Printer).where(Printer.id == printer_id, Printer.user_id == user.id)
    )
    printer = result.scalar_one_or_none()
    if printer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "printer not found")

    bbox = await get_or_compute_bbox(session, source=source, source_id=source_id)
    if bbox is None:
        return FitResponse(status="unknown", bbox=None, margin_pct=margin_pct)

    build = BuildVolume(
        x=printer.build_x_mm, y=printer.build_y_mm, z=printer.build_z_mm
    )
    ok = fits(bbox, build, margin_pct=margin_pct)
    return FitResponse(
        status="fits" if ok else "too_big",
        bbox=BboxOut(x=bbox.x, y=bbox.y, z=bbox.z),
        margin_pct=margin_pct,
    )
