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
    url: str, *, client: httpx.AsyncClient | None = None
) -> Bbox | None:
    """Download a model file and return its bounding box in mm.

    Returns None if the format isn't supported. Raises FileTooLargeError if the
    response exceeds MAX_FILE_BYTES. Caller should cache the result.
    """
    ext = _ext_from_url(url)
    if ext not in _SUPPORTED:
        return None
    file_type = ext.lstrip(".")

    own_client = client is None
    client = client or httpx.AsyncClient(timeout=60.0, follow_redirects=True)
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        cl = resp.headers.get("content-length")
        if cl and int(cl) > MAX_FILE_BYTES:
            raise FileTooLargeError(f"{url} is {cl} bytes (cap {MAX_FILE_BYTES})")
        data = resp.content
        if len(data) > MAX_FILE_BYTES:
            raise FileTooLargeError(f"{url} is {len(data)} bytes (cap {MAX_FILE_BYTES})")
    finally:
        if own_client:
            await client.aclose()

    return await asyncio.to_thread(_parse_bytes_sync, data, file_type)
