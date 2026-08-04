from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.ingestion import SmartphoneRecord


class Product(SmartphoneRecord):
    id: UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class PassportCreate(BaseModel):
    product_id: UUID


class Passport(BaseModel):
    id: UUID
    product_id: UUID
    current_version: int
    status: Literal["ACTIVE", "ARCHIVED"]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class PassportVersion(BaseModel):
    passport_id: UUID
    version: int
    graph_uri: str
    created_at: datetime
