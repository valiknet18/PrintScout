from typing import Any

import httpx

from app.sources.base import FileInfo, ModelStub

GRAPHQL_URL = "https://api.printables.com/graphql/"
MEDIA_BASE = "https://media.printables.com/"
WEB_BASE = "https://www.printables.com/"

SEARCH_QUERY = """
query PsSearch($q: String!, $limit: Int, $offset: Int, $paid: PaidEnum,
               $nozzleDiameters: [Float], $ordering: SearchChoicesEnum) {
  searchPrints2(query: $q, limit: $limit, offset: $offset, paid: $paid,
                nozzleDiameters: $nozzleDiameters, ordering: $ordering) {
    totalCount
    items {
      id
      slug
      name
      price
      ratingAvg
      downloadCount
      image { filePath }
      tags { name }
      previewFile {
        __typename
        ... on STLType { id name fileSize filePreviewPath }
      }
    }
  }
}
"""

POPULAR_QUERY = """
query PsPopular($limit: Int, $paid: PaidEnum, $ordering: String) {
  morePrints(limit: $limit, paid: $paid, ordering: $ordering) {
    cursor
    items {
      id
      slug
      name
      price
      ratingAvg
      downloadCount
      image { filePath }
      tags { name }
      previewFile {
        __typename
        ... on STLType { id name fileSize filePreviewPath }
      }
    }
  }
}
"""


def derive_stl_url(file_preview_path: str | None, name: str | None) -> str | None:
    """Direct CDN URL for an STL, derived from its preview-PNG path + filename."""
    if not file_preview_path or not name:
        return None
    folder, _, _ = file_preview_path.rpartition("/")
    if not folder:
        return None
    return f"{MEDIA_BASE}{folder}/{name}"


class PrintablesSource:
    name = "printables"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=15.0,
            headers={"user-agent": "printscout/0.1 (+https://t.me/printscout_bot)"},
        )

    @property
    def is_enabled(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 30,
        paid: str | None = "free",
        nozzle_mm: float | None = None,
    ) -> tuple[list[ModelStub], int]:
        variables: dict[str, Any] = {
            "q": query,
            "limit": page_size,
            "offset": max(0, (page - 1) * page_size),
            "ordering": "best_match",
        }
        if paid:
            variables["paid"] = paid
        if nozzle_mm is not None:
            variables["nozzleDiameters"] = [nozzle_mm]

        resp = await self._client.post(
            GRAPHQL_URL,
            json={"query": SEARCH_QUERY, "variables": variables, "operationName": "PsSearch"},
        )
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body:
            raise RuntimeError(f"Printables GraphQL errors: {body['errors']}")

        payload = body["data"]["searchPrints2"]
        items = [_print_to_stub(self.name, it) for it in payload["items"]]
        return items, int(payload.get("totalCount") or 0)

    async def popular(
        self, *, limit: int = 24, paid: str | None = "free"
    ) -> list[ModelStub]:
        variables: dict[str, Any] = {
            "limit": limit,
            "ordering": "-likes_count",
        }
        if paid:
            variables["paid"] = paid

        resp = await self._client.post(
            GRAPHQL_URL,
            json={
                "query": POPULAR_QUERY,
                "variables": variables,
                "operationName": "PsPopular",
            },
        )
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body:
            raise RuntimeError(f"Printables GraphQL errors: {body['errors']}")

        payload = body["data"]["morePrints"]
        return [_print_to_stub(self.name, it) for it in payload["items"]]

    async def get_files(self, source_id: str) -> list[FileInfo]:
        # TODO: implement print(id) -> filesType + downloadable URLs.
        return []

    async def aclose(self) -> None:
        await self._client.aclose()


def _print_to_stub(source_name: str, it: dict[str, Any]) -> ModelStub:
    file_path = (it.get("image") or {}).get("filePath")
    tags = [t["name"] for t in (it.get("tags") or []) if t.get("name")]
    preview = it.get("previewFile") or {}
    stl_url = (
        derive_stl_url(preview.get("filePreviewPath"), preview.get("name"))
        if preview.get("__typename") == "STLType"
        else None
    )
    return ModelStub(
        source=source_name,
        source_id=str(it["id"]),
        title=it["name"],
        url=f"{WEB_BASE}model/{it['id']}-{it['slug']}",
        thumbnail_url=f"{MEDIA_BASE}{file_path}" if file_path else None,
        is_free=it.get("price") in (None, "0", "0.00"),
        tags=tags,
        preview_stl_url=stl_url,
    )
