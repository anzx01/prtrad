from __future__ import annotations

from typing import Any

import httpx
from httpx import Timeout


class PolymarketApiError(RuntimeError):
    pass


class PolymarketGammaClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        # Configure retry transport
        transport = httpx.HTTPTransport(retries=3)

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=Timeout(timeout_seconds, connect=5.0),
            headers={"Accept": "application/json"},
            transport=transport,
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

        try:
            response = self._client.get("/events", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise PolymarketApiError(f"Gamma API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise PolymarketApiError(f"Gamma API request failed: {e}") from e

        payload = response.json()
        if isinstance(payload, list):
            return payload
        raise PolymarketApiError("Gamma /events 返回结构不是数组。")

    def close(self) -> None:
        self._client.close()


class PolymarketClobClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        # Configure retry transport
        transport = httpx.HTTPTransport(retries=3)

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=Timeout(timeout_seconds, connect=5.0),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            transport=transport,
        )

    def get_order_books(self, token_ids: list[str]) -> list[dict[str, Any]]:
        if not token_ids:
            return []

        payload = [{"token_id": token_id} for token_id in token_ids]

        try:
            response = self._client.post("/books", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise PolymarketApiError(f"CLOB API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise PolymarketApiError(f"CLOB API request failed: {e}") from e

        books = response.json()
        if isinstance(books, list):
            return books
        if isinstance(books, dict):
            return [books]
        raise PolymarketApiError("CLOB /books 返回结构不是对象数组。")

    def close(self) -> None:
        self._client.close()
