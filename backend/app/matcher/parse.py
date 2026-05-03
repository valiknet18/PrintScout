import asyncio
import io
from pathlib import PurePosixPath

import httpx
import trimesh

from app.matcher.fit import Bbox

_SUPPORTED = {".stl", ".3mf", ".obj"}
MAX_FILE_BYTES = 30 * 1024 * 1024  # 30 MiB


class FileTooLargeError(RuntimeError):
    pass


def _ext_from_url(url: str) -> str:
    return PurePosixPath(httpx.URL(url).path).suffix.lower()


def _parse_bytes_sync(data: bytes, file_type: str) -> Bbox:
    mesh = trimesh.load(io.BytesIO(data), file_type=file_type, force="mesh")
    extents = mesh.bounding_box.extents
    return Bbox(x=float(extents[0]), y=float(extents[1]), z=float(extents[2]))


async def parse_bbox_from_url(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    fmt: str | None = None,
) -> Bbox | None:
    """Download a model file and return its bounding box in mm.

    `fmt` (e.g. "stl", "3mf", "obj") is preferred when known. Otherwise we
    sniff the original URL, then fall back to the final URL after redirects
    (Thingiverse's `/v2/files/{id}/download` 302s to a CDN URL with the real
    extension).

    Returns None if format can't be determined or isn't supported. Raises
    FileTooLargeError when the response exceeds MAX_FILE_BYTES.
    """
    if not fmt:
        ext = _ext_from_url(url)
        if ext in _SUPPORTED:
            fmt = ext.lstrip(".")

    own_client = client is None
    client = client or httpx.AsyncClient(timeout=60.0, follow_redirects=True)
    try:
        resp = await client.get(url)
        resp.raise_for_status()

        if not fmt:
            ext = _ext_from_url(str(resp.url))
            if ext in _SUPPORTED:
                fmt = ext.lstrip(".")
        if not fmt:
            return None

        cl = resp.headers.get("content-length")
        if cl and int(cl) > MAX_FILE_BYTES:
            raise FileTooLargeError(f"{url} is {cl} bytes (cap {MAX_FILE_BYTES})")
        data = resp.content
        if len(data) > MAX_FILE_BYTES:
            raise FileTooLargeError(f"{url} is {len(data)} bytes (cap {MAX_FILE_BYTES})")
    finally:
        if own_client:
            await client.aclose()

    return await asyncio.to_thread(_parse_bytes_sync, data, fmt)
