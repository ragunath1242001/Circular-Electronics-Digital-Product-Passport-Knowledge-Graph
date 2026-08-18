from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

MetricId = Literal[
    "MET-001",
    "MET-002",
    "MET-003",
    "MET-004",
    "MET-005",
    "MET-006",
    "MET-007",
    "MET-008",
    "MET-009",
    "MET-010",
]
Granularity = Literal["day", "week", "month"]


class MetricBreakdown(BaseModel):
    key: str
    value: float | None
    numerator: int
    denominator: int
    components: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)


class SemanticMetric(BaseModel):
    metric_id: MetricId
    name: str
    value: float | None
    numerator: int | None
    denominator: int | None
    components: dict[str, int] = Field(default_factory=dict)
    breakdown: list[MetricBreakdown] = Field(default_factory=list)
    bucket_start: date | None = None
    calculation_version: str
    calculated_at: datetime


class MetricExplanation(BaseModel):
    metric_id: MetricId
    name: str
    purpose: str
    formula: str
    edge_cases: list[str]
    calculation_version: str


class MetricFilters(BaseModel):
    organisation: str | None = None
    domain: Literal["electronics", "battery"] | None = None
    from_date: date | None = None
    to_date: date | None = None
    granularity: Granularity | None = None
