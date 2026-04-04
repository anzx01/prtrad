"""标签质量服务"""
from sqlalchemy.orm import Session
from db.models import TagQualityMetric

class TagQualityService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_metrics(self):
        return []
