from __future__ import annotations

from typing import Any

import httpx


class PolymarketApiError(RuntimeError):
    pass


class PolymarketGammaClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={"Accept": "application/json"},
        )

    def list_events(
        self,
        *,
        limit: int,
        offset: int,
        active: bool,
        closed: bool,
        archived: bool,
        order: str = "id",
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        params = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "archived": str(archived).lower(),
            "order": order,
            "ascending": str(ascending).lower(),
        }
        response = self._client.get("/events", params=params)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        raise PolymarketApiError("Gamma /events 返回结构不是数组。")

    def close(self) -> None:
        self._client.close()


class PolymarketClobClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    def get_order_books(self, token_ids: list[str]) -> list[dict[str, Any]]:
        if not token_ids:
            return []
        payload = [{"token_id": token_id} for token_id in token_ids]
        response = self._client.post("/books", json=payload)
        response.raise_for_status()
        books = response.json()
        if isinstance(books, list):
            return books
        if isinstance(books, dict):
            return [books]
        raise PolymarketApiError("CLOB /books 返回结构不是对象数组。")

    def close(self) -> None:
        self._client.close()
