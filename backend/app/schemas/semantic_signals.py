from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ObservationType = Literal[
    "ontology_version",
    "class_usage",
    "property_usage",
    "namespace_usage",
    "term_classification",
    "mapping_used",
    "mapping_missing",
]
TermCategory = Literal["standard", "external_approved", "custom", "unknown", "deprecated"]


class SemanticObservation(BaseModel):
    document_id: str
    observation_type: ObservationType
    term_iri: str | None = None
    namespace: str | None = None
    category: TermCategory | None = None
    ontology_version: str | None = None
    occurrence_count: int = Field(default=1, ge=1)
    observed_at: datetime


class SignalBatch(BaseModel):
    documents: int
    observations: int
    occurrences: int


class SignalSummary(BaseModel):
    total_documents: int
    collected_documents: int
    observations: int
    occurrences: int
    by_type: dict[str, int]
    by_category: dict[str, int]
