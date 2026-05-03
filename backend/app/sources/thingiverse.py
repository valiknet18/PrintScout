"""Thingiverse REST adapter.

Docs (community-maintained — official portal is gated):
  https://www.thingiverse.com/developers
  https://www.thingiverse.com/developers/getting-started

Auth: OAuth bearer token. Without a token the adapter no-ops cleanly.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import httpx

from app.sources.base import FileInfo, ModelStub

API_BASE = "https://api.thingiverse.com"
WEB_BASE = "https://www.thingiverse.com"

log = logging.getLogger(__name__)

_PARSEABLE_EXT = {".stl", ".3mf", ".obj"}


class ThingiverseSource:
    name = "thingiverse"

    def __init__(self, token: str, client: httpx.AsyncClient | None = None) -> None:
        self._token = token
        self._client = client or httpx.AsyncClient(
            timeout=15.0,
            headers={
                "user-agent": "printscout/0.1 (+https://t.me/printscout_bot)",
                "accept": "application/json",
            },
        )

    @property
    def is_enabled(self) -> bool:
        return bool(self._token)

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 30,
        paid: str | None = "free",
        nozzle_mm: float | None = None,  # not exposed by Thingiverse search
    ) -> tuple[list[ModelStub], int]:
        if not self.is_enabled:
            return [], 0

        # Thingiverse has no native paid/free distinction — most things are free.
        # When the user explicitly asked for paid-only, skip this source entirely.
        if paid == "paid":
            return [], 0

        path = f"/search/{urllib.parse.quote(query, safe='')}"
        params = {"type": "things", "page": page, "per_page": page_size}
        try:
            resp = await self._client.get(
                f"{API_BASE}{path}",
                params=params,
                headers={"authorization": f"Bearer {self._token}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            log.exception("thingiverse search failed")
            return [], 0

        body = resp.json()
        # Response shape can be either {hits: [...], total: N} or a bare list,
        # depending on endpoint version. Handle both.
        if isinstance(body, list):
            raw_items = body
            total = len(body)
        else:
            raw_items = body.get("hits") or body.get("things") or []
            total = int(body.get("total") or len(raw_items))

        items: list[ModelStub] = []
        for it in raw_items:
            thing_id = str(it.get("id") or "")
            if not thing_id:
                continue
            items.append(
                ModelStub(
                    source=self.name,
                    source_id=thing_id,
                    title=it.get("name") or "(untitled)",
                    url=it.get("public_url") or f"{WEB_BASE}/thing:{thing_id}",
                    thumbnail_url=_pick_thumbnail(it),
                    is_free=not bool(it.get("is_purchased")),
                    tags=[],
                )
            )
        return items, total

    async def get_files(self, source_id: str) -> list[FileInfo]:
        if not self.is_enabled:
            return []
        try:
            resp = await self._client.get(
                f"{API_BASE}/things/{source_id}/files",
                headers={"authorization": f"Bearer {self._token}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            log.exception("thingiverse get_files failed for %s", source_id)
            return []

        out: list[FileInfo] = []
        for f in resp.json() or []:
            name = f.get("name") or ""
            ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
            if ext not in _PARSEABLE_EXT:
                continue
            url = f.get("download_url") or f.get("public_url")
            if not url:
                continue
            out.append(
                FileInfo(
                    file_id=str(f.get("id") or name),
                    file_url=url,
                    fmt=ext.lstrip("."),
                    size_bytes=f.get("size"),
                )
            )
        return out

    async def aclose(self) -> None:
        await self._client.aclose()


def _pick_thumbnail(thing: dict[str, Any]) -> str | None:
    if thing.get("thumbnail"):
        return thing["thumbnail"]
    di = thing.get("default_image") or {}
    if isinstance(di, dict):
        # default_image.url is the original; sizes[] holds rendered variants.
        return di.get("url")
    return None
