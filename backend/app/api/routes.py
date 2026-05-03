from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.schemas import PrinterIn, PrinterOut, UserOut
from app.core.db import get_session
from app.models import Printer, User

router = APIRouter(prefix="/api")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/printers", response_model=list[PrinterOut])
async def list_printers(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Printer]:
    result = await session.execute(
        select(Printer).where(Printer.user_id == user.id).order_by(Printer.id)
    )
    return list(result.scalars())


@router.post("/printers", response_model=PrinterOut, status_code=status.HTTP_201_CREATED)
async def create_printer(
    payload: PrinterIn,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Printer:
    printer = Printer(user_id=user.id, **payload.model_dump())
    session.add(printer)
    await session.commit()
    await session.refresh(printer)
    return printer


@router.delete("/printers/{printer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_printer(
    printer_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(Printer).where(Printer.id == printer_id, Printer.user_id == user.id)
    )
    printer = result.scalar_one_or_none()
    if printer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    await session.delete(printer)
    await session.commit()
