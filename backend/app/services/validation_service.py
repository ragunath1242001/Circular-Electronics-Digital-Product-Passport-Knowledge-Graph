from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pyshacl import validate as shacl_validate
from rdflib import RDF, Graph, Namespace

from app.schemas.validation import ValidationReport, ValidationResult

ONTOLOGY_ROOT = Path(__file__).resolve().parents[3] / "ontology"
SH = Namespace("http://www.w3.org/ns/shacl#")


class InvalidRdfError(ValueError):
    """Raised when submitted RDF cannot be parsed."""


@dataclass(frozen=True)
class ValidationOutcome:
    report: ValidationReport
    report_turtle: str


def _load_graph(directory: Path) -> Graph:
    graph = Graph()
    for path in sorted(directory.glob("*.ttl")):
        graph.parse(path, format="turtle")
    return graph


def validate_data(data: str, data_format: str = "turtle") -> ValidationOutcome:
    data_graph = Graph()
    try:
        data_graph.parse(data=data, format=data_format)
    except Exception as exc:
        raise InvalidRdfError(f"Invalid {data_format} RDF: {exc}") from exc

    conforms, report_graph, _ = shacl_validate(
        data_graph=data_graph,
        shacl_graph=_load_graph(ONTOLOGY_ROOT / "shapes"),
        ont_graph=_load_graph(ONTOLOGY_ROOT / "core"),
        inference="rdfs",
        advanced=True,
        meta_shacl=True,
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
