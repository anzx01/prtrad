from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from httpx import Timeout


logger = logging.getLogger("ptr.ingest.gamma")


class PolymarketApiError(RuntimeError):
    pass


def _make_transport() -> httpx.HTTPTransport:
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy:
        return httpx.HTTPTransport(retries=3, proxy=proxy)
    return httpx.HTTPTransport(retries=3)


class PolymarketGammaClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int,
        *,
        retry_max_attempts: int = 5,
        retry_base_delay_seconds: float = 0.5,
        retry_max_delay_seconds: float = 8.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=Timeout(timeout_seconds, connect=5.0),
            headers={"Accept": "application/json"},
            transport=_make_transport(),
        )
        self._retry_max_attempts = max(1, retry_max_attempts)
        self._retry_base_delay_seconds = max(0.0, retry_base_delay_seconds)
        self._retry_max_delay_seconds = max(self._retry_base_delay_seconds, retry_max_delay_seconds)

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

        return self._request_json_array("/events", params=params, endpoint_name="/events")

    def list_markets(
        self,
        *,
        limit: int,
        offset: int,
        active: bool | None = None,
        closed: bool | None = None,
        archived: bool | None = None,
        order: str = "id",
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()
        if archived is not None:
            params["archived"] = str(archived).lower()

        return self._request_json_array("/markets", params=params, endpoint_name="/markets")

    def _request_json_array(
        self,
        path: str,
        *,
        params: dict[str, str | int],
        endpoint_name: str,
    ) -> list[dict[str, Any]]:
        last_error: Exception | None = None

        for attempt in range(1, self._retry_max_attempts + 1):
            try:
                response = self._client.get(path, params=params)
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, list):
                    return payload
                raise PolymarketApiError(f"Gamma {endpoint_name} 返回结构不是数组。")
            except httpx.HTTPStatusError as e:
                last_error = e
                if not self._should_retry_status(e.response.status_code) or attempt >= self._retry_max_attempts:
                    raise PolymarketApiError(f"Gamma API error: {e.response.status_code}") from e
                self._sleep_before_retry(attempt, endpoint_name, e.response.headers.get("Retry-After"), e.response.status_code)
            except httpx.RequestError as e:
                last_error = e
                if attempt >= self._retry_max_attempts:
                    raise PolymarketApiError(f"Gamma API request failed: {e}") from e
                self._sleep_before_retry(attempt, endpoint_name, None, None)

        if last_error is not None:
            raise PolymarketApiError(f"Gamma API request failed: {last_error}") from last_error
        raise PolymarketApiError(f"Gamma {endpoint_name} request failed")

    @staticmethod
    def _should_retry_status(status_code: int) -> bool:
        return status_code in {429, 500, 502, 503, 504}

    def _sleep_before_retry(
        self,
        attempt: int,
        endpoint_name: str,
        retry_after: str | None,
        status_code: int | None,
    ) -> None:
        delay_seconds = self._retry_delay_seconds(attempt, retry_after)
        logger.warning(
            "gamma request retry scheduled endpoint=%s status=%s attempt=%s delay_seconds=%.2f",
            endpoint_name,
            status_code,
            attempt,
            delay_seconds,
        )
        time.sleep(delay_seconds)

    def _retry_delay_seconds(self, attempt: int, retry_after: str | None) -> float:
        if isinstance(retry_after, (str, int, float)):
            try:
                return min(self._retry_max_delay_seconds, max(0.0, float(retry_after)))
            except (TypeError, ValueError):
                pass
        if self._retry_base_delay_seconds <= 0:
            return 0.0
        exponential_delay = self._retry_base_delay_seconds * (2 ** (attempt - 1))
        return min(self._retry_max_delay_seconds, exponential_delay)

    def close(self) -> None:
        self._client.close()


class PolymarketClobClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=Timeout(timeout_seconds, connect=5.0),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            transport=_make_transport(),
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
