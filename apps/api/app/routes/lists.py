from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from services.lists import ListService

router = APIRouter(prefix="/lists", tags=["lists"])

class ListEntriesResponse(BaseModel):
    entries: list[dict[str, Any]]
    total: int

@router.get("/entries", response_model=ListEntriesResponse)
def list_entries(
    request: Request,
    session: Session = Depends(get_db),
    list_type: str | None = None,
) -> ListEntriesResponse:
    """List all list entries."""
    service = ListService(db=session)
    entries = service.list_entries(list_type=list_type)
    
    entry_data = [
        {
            "id": str(entry.id),
            "list_type": entry.list_type,
            "entry_type": entry.entry_type,
            "entry_value": entry.entry_value,
            "match_mode": entry.match_mode,
            "is_active": entry.is_active,
            "created_at": entry.created_at.isoformat(),
        }
        for entry in entries
    ]
    
    return ListEntriesResponse(entries=entry_data, total=len(entry_data))
