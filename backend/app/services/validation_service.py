from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from pyshacl import validate as shacl_validate
from rdflib import RDF, Graph, Namespace

from app.db.validation_runs import (
    list_pending_documents,
    save_document_validations,
)
from app.schemas.validation import (
    DocumentValidation,
    ValidationBatch,
    ValidationReport,
    ValidationResult,
)
from app.services.graph_store import get_graph
from app.services.semantic_registry import get_registry

ONTOLOGY_ROOT = Path(__file__).resolve().parents[3] / "ontology"
SH = Namespace("http://www.w3.org/ns/shacl#")


class InvalidRdfError(ValueError):
    """Raised when submitted RDF cannot be parsed."""


@dataclass(frozen=True)
class ValidationOutcome:
    report: ValidationReport
    report_turtle: str


@lru_cache
def _load_graph(paths: tuple[Path, ...]) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path, format="turtle")
    return graph


def validate_data(
    data: str,
    data_format: str = "turtle",
    shape_paths: tuple[str, ...] | None = None,
    meta_shacl: bool = True,
) -> ValidationOutcome:
    data_graph = Graph()
    try:
        data_graph.parse(data=data, format=data_format)
    except Exception as exc:
        raise InvalidRdfError(f"Invalid {data_format} RDF: {exc}") from exc

    shape_files = (
        tuple(ONTOLOGY_ROOT / path for path in shape_paths)
        if shape_paths
        else tuple(sorted((ONTOLOGY_ROOT / "shapes").glob("*.ttl")))
    )
    ontology_files = tuple(sorted((ONTOLOGY_ROOT / "core").glob("*.ttl")))
    conforms, report_graph, _ = shacl_validate(
        data_graph=data_graph,
        shacl_graph=_load_graph(shape_files),
        ont_graph=_load_graph(ontology_files),
        inference="rdfs",
        advanced=True,
        meta_shacl=meta_shacl,
        allow_infos=True,
        allow_warnings=True,
    )
    if not isinstance(report_graph, Graph):
        raise RuntimeError(str(report_graph))

    results: list[ValidationResult] = []
    for node in report_graph.subjects(RDF.type, SH.ValidationResult):
        severity_iri = report_graph.value(node, SH.resultSeverity)
        severity = str(severity_iri).rsplit("#", 1)[-1]
        if severity not in {"Violation", "Warning", "Info"}:
            severity = "Violation"
        results.append(
            ValidationResult(
                focus_node=str(report_graph.value(node, SH.focusNode) or ""),
                path=str(report_graph.value(node, SH.resultPath))
                if report_graph.value(node, SH.resultPath)
                else None,
                constraint_component=str(report_graph.value(node, SH.sourceConstraintComponent))
                if report_graph.value(node, SH.sourceConstraintComponent)
                else None,
                severity=severity,  # type: ignore[arg-type]
                message=str(report_graph.value(node, SH.resultMessage) or "Validation failed."),
                source_shape=str(report_graph.value(node, SH.sourceShape))
                if report_graph.value(node, SH.sourceShape)
                else None,
            )
        )

    counts = {
        severity: sum(result.severity == severity for result in results)
        for severity in ("Violation", "Warning", "Info")
    }
    report = ValidationReport(
        id=uuid4(),
        conforms=bool(conforms),
        created_at=datetime.now(UTC),
        violations=counts["Violation"],
        warnings=counts["Warning"],
        info=counts["Info"],
        results=results,
    )
    return ValidationOutcome(
        report=report,
        report_turtle=str(report_graph.serialize(format="turtle")),
    )


def validate_pending_documents(limit: int) -> ValidationBatch:
    documents = list_pending_documents(limit)
    profiles = {profile.id: profile for profile in get_registry().profiles}
    validations: list[DocumentValidation] = []
    for document in documents:
        profile = profiles.get(document.semantic_profile_id)
        if profile is None or profile.domain != document.domain:
            raise ValueError(
                f"Unknown semantic profile {document.semantic_profile_id!r} for {document.domain}."
            )
        outcome = validate_data(
            get_graph(document.graph_uri).decode("utf-8"),
            shape_paths=tuple(profile.shape_paths),
            meta_shacl=False,
        )
        validations.append(DocumentValidation(document=document, report=outcome.report))

    save_document_validations(validations)
    conforming = sum(item.report.conforms for item in validations)
    return ValidationBatch(
        documents=len(validations),
        conforming=conforming,
        nonconforming=len(validations) - conforming,
        observations=sum(len(item.report.results) for item in validations),
    )
