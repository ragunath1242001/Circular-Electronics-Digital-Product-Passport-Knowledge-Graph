from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

EvidenceCandidateType = Literal[
    "EMERGING_CONCEPT",
    "MAPPING_NEEDED",
    "DOCUMENTATION_FRICTION",
    "DEPRECATION_MIGRATION_PROBLEM",
    "SHACL_RULE_FRICTION",
    "CROSS_SECTOR_MODEL_CONFLICT",
    "VERSION_MIGRATION_FRICTION",
]
EvidenceStatus = Literal["NEW", "MARKED_FOR_REVIEW", "DISMISSED"]
EvidenceTrend = Literal["increasing", "stable", "decreasing", "insufficient_history"]
MappingStatus = Literal["missing", "approved", "not_applicable"]
type EvidenceMetricValue = str | int | float | bool | list[str]


class EvidenceCandidateDraft(BaseModel):
    id: UUID
    candidate_key: str
    candidate_type: EvidenceCandidateType
    label: str
    affected_concepts: list[str]
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int = Field(ge=0)
    organisation_count: int = Field(ge=0)
    domain_count: int = Field(ge=0)
    trend: EvidenceTrend
    growth_rate: float | None = None
    persistence_days: int = Field(ge=1)
    mapping_status: MappingStatus
    conformance_impact: int = Field(ge=0)
    metrics: dict[str, EvidenceMetricValue]
    recommendation: str
    source_incident_id: UUID | None = None
    evidence_references: list[str]
    evidence_version: str


class EvidenceCandidate(EvidenceCandidateDraft):
    status: EvidenceStatus
    annotation: str | None = None
    created_at: datetime
    updated_at: datetime


class EvidenceUpdate(BaseModel):
    status: EvidenceStatus | None = None
    annotation: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_change(self) -> "EvidenceUpdate":
        if self.status is None and "annotation" not in self.model_fields_set:
            raise ValueError("status or annotation is required")
        return self


class EvidenceRun(BaseModel):
    evidence_version: str
    candidates: int
