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
    constraint_component: str | None = None
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


class StoredSemanticDocument(BaseModel):
    document_id: str
    organisation_id: str
    domain: str
    semantic_profile_id: str
    declared_ontology_version: str
    graph_uri: str


class DocumentValidation(BaseModel):
    document: StoredSemanticDocument
    report: ValidationReport


class ValidationBatch(BaseModel):
    documents: int
    conforming: int
    nonconforming: int
    observations: int


class ValidationSummary(BaseModel):
    total_documents: int
    validated_documents: int
    conforming_documents: int
    nonconforming_documents: int
    conformance_rate: float
    violations: int
    warnings: int
    info: int
