"""监控服务"""
from sqlalchemy.orm import Session
from db.models import AuditLog

class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_metrics(self):
        return {"status": "ok", "metrics": {}}
