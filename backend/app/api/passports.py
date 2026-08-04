from html import escape
from io import BytesIO
from typing import Literal
from uuid import UUID

import psycopg
import qrcode  # type: ignore[import-untyped]
import qrcode.image.svg  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
from app.db.passports import (
    archive_passport,
    archive_product,
    create_product,
    get_passport,
    get_product,
    get_product_passport,
    list_passport_versions,
    list_passports,
    list_products,
    update_product,
)
from app.schemas.ingestion import SmartphoneRecord
from app.schemas.passports import Passport, PassportCreate, PassportVersion, Product
from app.schemas.validation import ValidationReport
from app.services.graph_store import GraphStoreError
from app.services.passport_service import (
    PassportConflictError,
    PassportNotFoundError,
    create_product_passport,
    export_passport_graph,
    validate_passport_graph,
    version_product_passport,
)

router = APIRouter(prefix="/api/v1", tags=["products", "passports"])
public_router = APIRouter(tags=["public"])


def _database_error(exc: psycopg.Error) -> HTTPException:
    if isinstance(exc, psycopg.errors.UniqueViolation):
        return HTTPException(status_code=409, detail="The product or passport already exists.")
    return HTTPException(status_code=503, detail="Product passport metadata is unavailable.")


def _passport_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PassportNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PassportConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, GraphStoreError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, psycopg.Error):
        return _database_error(exc)
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/products", response_model=list[Product])
def products(
    include_archived: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Product]:
    try:
        return list_products(include_archived, limit)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc


@router.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def post_product(record: SmartphoneRecord) -> Product:
    try:
        return create_product(record)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc


@router.get("/products/{product_id}", response_model=Product)
def product(product_id: UUID) -> Product:
    try:
        result = get_product(product_id)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return result


@router.put("/products/{product_id}", response_model=Product)
def put_product(product_id: UUID, record: SmartphoneRecord) -> Product:
    try:
        result = update_product(product_id, record)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Active product not found.")
    return result


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID) -> Response:
    try:
        archived = archive_product(product_id)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc
    if not archived:
        raise HTTPException(status_code=404, detail="Active product not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/products/{product_id}/passport", response_model=Passport)
def product_passport(product_id: UUID) -> Passport:
    try:
        result = get_product_passport(product_id)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Product passport not found.")
    return result


@router.get("/products/{product_id}/graph")
def product_graph(product_id: UUID) -> Response:
    passport = product_passport(product_id)
    return passport_export(passport.id, "turtle", None)


@router.get("/passports", response_model=list[Passport])
def passports(
    include_archived: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Passport]:
    try:
        return list_passports(include_archived, limit)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc


@router.post("/passports", response_model=Passport, status_code=status.HTTP_201_CREATED)
def post_passport(request: PassportCreate) -> Passport:
    try:
        return create_product_passport(request.product_id)
    except Exception as exc:
        raise _passport_error(exc) from exc


@router.get("/passports/{passport_id}", response_model=Passport)
def passport(passport_id: UUID) -> Passport:
    try:
        result = get_passport(passport_id)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Passport not found.")
    return result


@router.put("/passports/{passport_id}", response_model=Passport)
def put_passport(passport_id: UUID) -> Passport:
    try:
        return version_product_passport(passport_id)
    except Exception as exc:
        raise _passport_error(exc) from exc


@router.delete("/passports/{passport_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_passport(passport_id: UUID) -> Response:
    try:
        archived = archive_passport(passport_id)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc
    if not archived:
        raise HTTPException(status_code=404, detail="Active passport not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/passports/{passport_id}/validate", response_model=ValidationReport)
def validate_passport(passport_id: UUID) -> ValidationReport:
    try:
        return validate_passport_graph(passport_id).report
    except Exception as exc:
        raise _passport_error(exc) from exc


@router.get("/passports/{passport_id}/versions", response_model=list[PassportVersion])
def passport_versions(passport_id: UUID) -> list[PassportVersion]:
    passport(passport_id)
    try:
        return list_passport_versions(passport_id)
    except psycopg.Error as exc:
        raise _database_error(exc) from exc


@router.get("/passports/{passport_id}/export")
def passport_export(
    passport_id: UUID,
    rdf_format: Literal["turtle", "json-ld"] = Query(default="turtle", alias="format"),
    version: int | None = Query(default=None, ge=1),
) -> Response:
    try:
        data = export_passport_graph(passport_id, version, rdf_format)
    except Exception as exc:
        raise _passport_error(exc) from exc
    media_type = "text/turtle" if rdf_format == "turtle" else "application/ld+json"
    return Response(data, media_type=media_type)


@router.get("/passports/{passport_id}/qr")
def passport_qr(passport_id: UUID) -> Response:
    passport(passport_id)
    url = f"{get_settings().api_base_url.rstrip('/')}/passports/{passport_id}"
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    return Response(
        output.getvalue(),
        media_type="image/svg+xml",
        headers={"X-Passport-URL": url},
    )


@public_router.get("/passports/{passport_id}", response_class=HTMLResponse)
def public_passport(passport_id: UUID) -> HTMLResponse:
    stored_passport = passport(passport_id)
    stored_product = product(stored_passport.product_id)
    export_url = f"/api/v1/passports/{passport_id}/export"
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport"
content="width=device-width,initial-scale=1"><title>{escape(stored_product.product_name)}</title>
</head><body><main><p>Digital Product Passport</p>
<h1>{escape(stored_product.product_name)}</h1>
<dl><dt>Product ID</dt><dd>{escape(stored_product.product_identifier)}</dd>
<dt>Model</dt><dd>{escape(stored_product.model_number)}</dd>
<dt>Manufacturer</dt><dd>{escape(stored_product.manufacturer_name)}</dd>
<dt>Passport version</dt><dd>{stored_passport.current_version}</dd></dl>
<p><a href="{export_url}?format=json-ld">JSON-LD</a> ·
<a href="{export_url}?format=turtle">Turtle</a></p></main></body></html>"""
    )
