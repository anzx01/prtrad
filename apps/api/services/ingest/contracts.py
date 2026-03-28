from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class NormalizedMarketRecord:
    market_id: str
    event_id: str | None
    condition_id: str | None
    question: str
    description: str | None
    resolution_criteria: str | None
    creation_time: datetime | None
    open_time: datetime | None
    close_time: datetime | None
    resolution_time: datetime | None
    final_resolution: str | None
    market_status: str | None
    category_raw: str | None
    related_tags: list[dict[str, Any]] | None
    outcomes: list[str] | None
    clob_token_ids: list[str] | None
    source_updated_at: datetime | None
    source_payload: dict[str, Any]
