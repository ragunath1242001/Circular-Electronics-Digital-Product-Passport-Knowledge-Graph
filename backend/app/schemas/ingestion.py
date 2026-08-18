from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

JobStatus = Literal[
    "PENDING",
    "RUNNING",
    "MAPPING",
    "VALIDATING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
    "QUARANTINED",
]


class SmartphoneRecord(BaseModel):
    product_identifier: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9-]+$")
    product_name: str = Field(min_length=1, max_length=200)
    model_number: str = Field(min_length=1, max_length=80)
    manufacturer_name: str = Field(min_length=1, max_length=200)
    manufacturing_date: date
    repairability_score: Decimal = Field(ge=0, le=10)
    software_support_years: int = Field(ge=0, le=30)
    carbon_kg_co2e: Decimal = Field(gt=0)
    battery_identifier: str = Field(min_length=3, max_length=80)
    battery_chemistry: str = Field(min_length=1, max_length=100)
    battery_capacity_mah: Decimal = Field(gt=0)
    battery_cycle_endurance: int = Field(gt=0)
    battery_user_replaceable: bool
    battery_carbon_kg_co2e: Decimal = Field(gt=0)
    display_identifier: str = Field(min_length=3, max_length=80)
    supplier_name: str = Field(min_length=1, max_length=200)
    material_name: str = Field(min_length=1, max_length=100)
    material_origin: str = Field(min_length=1, max_length=200)
    recycled_content_percentage: Decimal = Field(ge=0, le=100)

    @field_validator("manufacturing_date")
    @classmethod
    def manufacturing_date_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("manufacturing date cannot be in the future")
        return value


class SemanticDocumentEnvelope(BaseModel):
    document_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    external_identifier: str = Field(min_length=1, max_length=200)
    organisation_id: str = Field(min_length=1, max_length=100)
    domain: Literal["electronics", "battery"]
    semantic_profile_id: str = Field(min_length=1, max_length=100)
    declared_ontology_version: str = Field(min_length=1, max_length=40)
    document_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload: dict[str, Any]


class IngestionJob(BaseModel):
    id: UUID
    source_system: str
    file_name: str
    data_format: Literal["csv", "json", "jsonl"]
    mapping_version: str
    status: JobStatus
    total_records: int = 0
    imported_records: int = 0
    duplicate_records: int = 0
    quarantined_records: int = 0
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


class IngestionError(BaseModel):
    id: int
    job_id: UUID
    record_number: int
    product_identifier: str | None = None
    error_code: str
    message: str
    raw_record: dict[str, Any]
    created_at: datetime
