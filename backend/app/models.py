from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    tg_username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    printers: Mapped[list["Printer"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Printer(Base):
    __tablename__ = "printers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(16))  # fdm | resin
    build_x_mm: Mapped[float] = mapped_column(Float)
    build_y_mm: Mapped[float] = mapped_column(Float)
    build_z_mm: Mapped[float] = mapped_column(Float)
    nozzle_mm: Mapped[float | None] = mapped_column(Float)
    materials: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="printers")


class CachedModel(Base):
    __tablename__ = "cached_models"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_cached_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    raw_meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    files: Mapped[list["ModelFile"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


class ModelFile(Base):
    __tablename__ = "model_files"
    __table_args__ = (
        UniqueConstraint("cached_model_id", "file_id", name="uq_model_file"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cached_model_id: Mapped[int] = mapped_column(
        ForeignKey("cached_models.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[str] = mapped_column(String(128))
    file_url: Mapped[str] = mapped_column(Text)
    fmt: Mapped[str] = mapped_column(String(8))  # stl | 3mf | obj
    bbox_x_mm: Mapped[float | None] = mapped_column(Float)
    bbox_y_mm: Mapped[float | None] = mapped_column(Float)
    bbox_z_mm: Mapped[float | None] = mapped_column(Float)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    model: Mapped[CachedModel] = relationship(back_populates="files")
