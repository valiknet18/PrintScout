"""Source registry — built once at process start from settings."""

from __future__ import annotations

from functools import lru_cache

from app.core.settings import get_settings
from app.sources.base import SourceAdapter
from app.sources.printables import PrintablesSource
from app.sources.thingiverse import ThingiverseSource


@lru_cache
def get_sources() -> dict[str, SourceAdapter]:
    settings = get_settings()
    return {
        PrintablesSource.name: PrintablesSource(),
        ThingiverseSource.name: ThingiverseSource(token=settings.thingiverse_token),
    }


def get_source(name: str) -> SourceAdapter | None:
    return get_sources().get(name)


def enabled_sources() -> list[SourceAdapter]:
    return [s for s in get_sources().values() if s.is_enabled]
