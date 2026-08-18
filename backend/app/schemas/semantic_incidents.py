from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DetectorType = Literal[
    "DET-001",
    "DET-002",
    "DET-003",
    "DET-004",
    "DET-005",
    "DET-006",
]
IncidentSeverity = Literal["info", "warning", "critical"]
IncidentStatus = Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"]
type IncidentValue = str | int | float | bool | list[str]


class DetectorConfig(BaseModel):
    detector_version: str
    unknown_term_min_occurrences: int = Field(ge=1)
    deprecated_term_min_occurrences: int = Field(ge=1)
    legacy_version_share_threshold: float = Field(ge=0, le=1)
    version_increase_periods: int = Field(ge=2)
    custom_term_share_threshold: float = Field(ge=0, le=1)
    custom_growth_delta: float = Field(ge=0, le=1)
    custom_growth_periods: int = Field(ge=2)
    fragmentation_threshold: float = Field(ge=0, le=1)
    mapping_gap_min_occurrences: int = Field(ge=1)


class IncidentCandidate(BaseModel):
    detector_type: DetectorType
    severity: IncidentSeverity
    dimensions: dict[str, IncidentValue]
    affected_entities: dict[str, IncidentValue]
    observed_values: dict[str, IncidentValue]
    baseline: dict[str, IncidentValue]
    threshold_rule: str
    evidence_references: list[str]
    explanation: str
    detector_version: str


class SemanticIncident(IncidentCandidate):
    id: UUID
    status: IncidentStatus
    opened_at: datetime
    last_detected_at: datetime
    closed_at: datetime | None = None


class DetectorRun(BaseModel):
    detector_version: str
    candidates: int
    open_incidents: int
