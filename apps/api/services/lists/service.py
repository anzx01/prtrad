"""名单管理服务"""
from sqlalchemy.orm import Session
from db.models import ListEntry, ListVersion

class ListService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_entries(self, list_type: str | None = None):
        from sqlalchemy import select
        query = select(ListEntry)
        if list_type:
            query = query.where(ListEntry.list_type == list_type)
        return list(self.db.scalars(query).all())
