from datetime import datetime
from typing import Literal

from pydantic import BaseModel

type DashboardMetricValue = str | int | float | bool | None


class EcosystemSummary(BaseModel):
    documents: int
    organisations: int
    domains: dict[str, int]
    ontology_versions: dict[str, int]
    main_metrics: dict[str, float | None]
    generated_at: datetime


class TermUsage(BaseModel):
    term_iri: str
    category: Literal["unknown", "deprecated", "custom", "mapping_missing"]
    occurrences: int
    documents: int
    organisations: int
    domains: list[str]
    first_seen: datetime
    last_seen: datetime


class ConstraintUsage(BaseModel):
    id: str
    profile: str
    path: str | None
    component: str
    severity: str
    message: str
    violations: int
    documents: int
    organisations: int
    domains: list[str]
    first_seen: datetime
    last_seen: datetime
    evidence_references: list[str]


class OrganisationAdoption(BaseModel):
    organisation_id: str
    documents: int
    current_documents: int
    adoption_rate: float


class OntologyAdoption(BaseModel):
    ontology_id: str
    current_version: str
    documents: int
    current_documents: int
    adoption_rate: float
    version_distribution: dict[str, int]
    lagging_organisations: list[OrganisationAdoption]


class OrganisationOverview(BaseModel):
    organisation_id: str
    documents: int
    domains: dict[str, int]
    profiles: dict[str, int]
    ontology_versions: dict[str, int]
    conformance_rate: float
    metric_values: dict[str, float | None]
