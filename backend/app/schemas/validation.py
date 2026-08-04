from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ValidationRequest(BaseModel):
    data: str = Field(min_length=1, max_length=2_000_000)
    format: Literal["turtle", "json-ld"] = "turtle"


class ValidationResult(BaseModel):
    focus_node: str
    path: str | None = None
    severity: Literal["Violation", "Warning", "Info"]
    message: str
    source_shape: str | None = None


class ValidationReport(BaseModel):
    id: UUID
    conforms: bool
    created_at: datetime
    violations: int
    warnings: int
    info: int
    results: list[ValidationResult]

