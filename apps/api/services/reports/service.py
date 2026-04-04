"""报告服务"""
from sqlalchemy.orm import Session
from db.models import M2Report

class ReportService:
    def __init__(self, db: Session):
        self.db = db
    
    def list_reports(self):
        return []
