from uuid import UUID, uuid4

from rdflib import Graph

from app.db.passports import (
    add_passport_version,
    create_passport,
    get_passport,
    get_passport_version,
    get_product,
)
from app.db.validation_runs import save_validation_run
from app.schemas.ingestion import SmartphoneRecord
from app.schemas.passports import Passport, Product
from app.semantic.graph_builder import record_to_graph
from app.services.graph_store import delete_graph, get_graph, put_graph
from app.services.validation_service import ValidationOutcome, validate_data


class PassportNotFoundError(LookupError):
    pass


class PassportConflictError(RuntimeError):
    pass


def _graph_uri(passport_id: UUID, version: int) -> str:
    return f"urn:dpp:graph:passport:{passport_id}:v{version}"


def _store_graph(product: Product, passport_id: UUID, version: int) -> str:
    record = SmartphoneRecord.model_validate(product.model_dump())
    graph = record_to_graph(record, "product-api", passport_id, version)
    outcome = validate_data(str(graph.serialize(format="turtle")))
    save_validation_run(outcome.report, outcome.report_turtle)
    if not outcome.report.conforms:
        raise ValueError("Generated passport graph did not pass SHACL validation.")
    graph_data = graph.serialize(format="turtle", encoding="utf-8")
    assert isinstance(graph_data, bytes)
    graph_uri = _graph_uri(passport_id, version)
    put_graph(graph_data, graph_uri)
    return graph_uri


def create_product_passport(product_id: UUID) -> Passport:
    product = get_product(product_id)
    if product is None:
        raise PassportNotFoundError("Product not found.")
    if product.archived_at:
        raise PassportConflictError("Archived products cannot receive a passport.")
    passport_id = uuid4()
    graph_uri = _store_graph(product, passport_id, 1)
    try:
        return create_passport(passport_id, product_id, graph_uri)
    except Exception:
        delete_graph(graph_uri)
        raise


def version_product_passport(passport_id: UUID) -> Passport:
    passport = get_passport(passport_id)
    if passport is None:
        raise PassportNotFoundError("Passport not found.")
    if passport.status == "ARCHIVED":
        raise PassportConflictError("Archived passports cannot be versioned.")
    product = get_product(passport.product_id)
    if product is None or product.archived_at:
        raise PassportConflictError("The passport product is archived or unavailable.")
    version = passport.current_version + 1
    graph_uri = _store_graph(product, passport_id, version)
    updated = add_passport_version(passport_id, version, graph_uri)
    if updated is None:
        raise PassportConflictError("Passport changed concurrently; retry the request.")
    return updated


def export_passport_graph(passport_id: UUID, version: int | None, rdf_format: str) -> bytes:
    stored_version = get_passport_version(passport_id, version)
    if stored_version is None:
        raise PassportNotFoundError("Passport version not found.")
    turtle = get_graph(stored_version.graph_uri)
    if rdf_format == "turtle":
        return turtle
    graph = Graph().parse(data=turtle.decode(), format="turtle")
    serialized = graph.serialize(format="json-ld", indent=2, encoding="utf-8")
    assert isinstance(serialized, bytes)
    return serialized


def validate_passport_graph(passport_id: UUID) -> ValidationOutcome:
    turtle = export_passport_graph(passport_id, None, "turtle")
    outcome = validate_data(turtle.decode())
    save_validation_run(outcome.report, outcome.report_turtle)
    return outcome
