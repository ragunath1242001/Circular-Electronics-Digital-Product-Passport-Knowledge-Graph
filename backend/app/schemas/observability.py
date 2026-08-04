from datetime import date, datetime

from pydantic import BaseModel


class FilterOptions(BaseModel):
    manufacturers: list[str]
    suppliers: list[str]
    models: list[str]


class TrendPoint(BaseModel):
    date: date
    runs: int
    passed: int
    violations: int


class TermUsage(BaseModel):
    term: str
    count: int
    controlled: bool


class RuleFailure(BaseModel):
    rule: str
    count: int


class SupplierScore(BaseModel):
    supplier: str
    products: int
    completeness: float


class VersionUsage(BaseModel):
    version: str
    products: int


class ObservabilityMetrics(BaseModel):
    generated_at: datetime
    applied_filters: dict[str, str]
    available_filters: FilterOptions
    products: int
    passports: int
    validation_runs: int
    quality_score: float
    score_components: dict[str, float]
    score_weights: dict[str, float]
    conformance_rate: float
    supplier_completeness: float
    carbon_completeness: float
    repair_completeness: float
    recycling_completeness: float
    missing_mandatory_fields: int
    missing_provenance: int
    unknown_vocabulary_terms: int
    deprecated_term_usage: int
    duplicate_entity_candidates: int
    vocabulary_usage: list[TermUsage]
    ontology_versions: list[VersionUsage]
    supplier_scores: list[SupplierScore]
    top_failing_rules: list[RuleFailure]
    validation_trend: list[TrendPoint]
