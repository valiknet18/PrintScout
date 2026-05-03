from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ModelStub:
    """A search hit before file-level enrichment."""

    source: str
    source_id: str
    title: str
    url: str
    thumbnail_url: str | None
    is_free: bool
    tags: list[str]
    # Direct download URL of a representative STL/3MF/OBJ for dimension parsing.
    # None when the source doesn't expose one (file gated, paid-only, no preview).
    preview_stl_url: str | None = None


@dataclass(slots=True)
class FileInfo:
    """One downloadable file belonging to a model."""

    file_id: str
    file_url: str
    fmt: str  # stl | 3mf | obj | ...
    size_bytes: int | None = None


class SourceAdapter(Protocol):
    name: str
    is_enabled: bool

    async def search(
        self, query: str, *, page: int = 1, page_size: int = 30, **kwargs
    ) -> tuple[list[ModelStub], int]: ...

    async def get_files(self, source_id: str) -> list[FileInfo]: ...
