from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ReportType = Literal["compliance", "sustainability", "supplier-quality", "certificate"]


class ReportRequest(BaseModel):
    report_type: ReportType


class ReportJob(BaseModel):
    id: UUID
    report_type: ReportType
    status: Literal["COMPLETED", "FAILED"]
    row_count: int
    summary: dict[str, int | float | str]
    sources: list[str]
    generated_at: datetime


class AuditLog(BaseModel):
    id: UUID
    actor: str
    action: str
    entity_type: str
    entity_id: str
    result: str
    details: dict[str, int | float | str]
    created_at: datetime
