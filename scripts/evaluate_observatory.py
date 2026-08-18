import argparse
import json
import tempfile
from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from urllib.request import urlopen

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from scripts.generate_synthetic import generate, load_scenario

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TRUTH = ROOT / "data" / "synthetic" / "generated" / "ground-truth.jsonl"
DEFAULT_SUMMARY = ROOT / "data" / "synthetic" / "generated" / "summary.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "observatory-evaluation.json"
DEFAULT_MARKDOWN = ROOT / "artifacts" / "observatory-evaluation.md"


def classification(expected: set[str], observed: set[str]) -> dict[str, int | float]:
    true_positive = len(expected & observed)
    false_positive = len(observed - expected)
    false_negative = len(expected - observed)
    precision = true_positive / (true_positive + false_positive) if observed else 0.0
    recall = true_positive / (true_positive + false_negative) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "expected": len(expected),
        "observed": len(observed),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _truth(path: Path) -> dict[str, set[str]]:
    grouped: defaultdict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as lines:
        for line in lines:
            row = json.loads(line)
            grouped[str(row["fault_type"])].add(str(row["document_id"]))
    return dict(grouped)


def _connect() -> psycopg.Connection[dict[str, Any]]:
    settings = get_settings()
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        row_factory=dict_row,
    )


def _document_sets(connection: psycopg.Connection[dict[str, Any]]) -> dict[str, set[str]]:
    queries = {
        "unknown_term": """
            SELECT DISTINCT document_id FROM semantic_observations
            WHERE observation_type = 'term_classification' AND category = 'unknown'
        """,
        "deprecated_term": """
            SELECT DISTINCT document_id FROM semantic_observations
            WHERE observation_type = 'term_classification' AND category = 'deprecated'
        """,
        "mapping_gap": """
            SELECT DISTINCT document_id FROM semantic_observations
            WHERE observation_type = 'mapping_missing'
        """,
        "legacy_version": """
            SELECT DISTINCT document_id FROM semantic_observations
            WHERE observation_type = 'ontology_version' AND category = 'deprecated'
        """,
    }
    return {
        name: {str(row["document_id"]) for row in connection.execute(query).fetchall()}
        for name, query in queries.items()
    }


def _metric_checks(
    connection: psycopg.Connection[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, dict[str, float | bool]]:
    rows = connection.execute(
        """
        SELECT category, SUM(occurrence_count) AS occurrences
        FROM semantic_observations
        WHERE observation_type = 'term_classification'
        GROUP BY category
        """
    ).fetchall()
    categories = {str(row["category"]): int(row["occurrences"]) for row in rows}
    mapping = connection.execute(
        """
        SELECT term_iri, BOOL_OR(observation_type = 'mapping_used') AS mapped
        FROM semantic_observations
        WHERE observation_type IN ('mapping_used', 'mapping_missing')
        GROUP BY term_iri
        """
    ).fetchall()
    metrics = {item["metric_id"]: item for item in _json_url("/api/v1/metrics")}
    total_terms = sum(categories.values())
    expected = {
        "MET-001": int(summary["ontology_versions"]["2.0.0"]) / int(summary["documents"]),
        "MET-002": (
            categories.get("standard", 0) + categories.get("external_approved", 0)
        ) / total_terms,
        "MET-003": categories.get("custom", 0) / total_terms,
        "MET-004": categories.get("unknown", 0) / total_terms,
        "MET-008": sum(bool(row["mapped"]) for row in mapping) / len(mapping),
        "MET-010": categories.get("deprecated", 0)
        / (categories.get("standard", 0) + categories.get("deprecated", 0)),
    }
    return {
        metric_id: {
            "expected": round(value, 4),
            "observed": float(metrics[metric_id]["value"]),
            "pass": round(value, 4) == float(metrics[metric_id]["value"]),
        }
        for metric_id, value in expected.items()
    }


def _fragmentation(connection: psycopg.Connection[dict[str, Any]]) -> dict[str, object]:
    config = json.loads((ROOT / "data" / "detectors.json").read_text(encoding="utf-8"))
    terms = (
        "https://example.org/dpp/chemistry",
        "https://example.org/dpp/batteryChemistry",
    )
    rows = connection.execute(
        """
        SELECT term_iri, SUM(occurrence_count) AS occurrences
        FROM semantic_observations
        WHERE observation_type = 'term_classification' AND term_iri = ANY(%s)
        GROUP BY term_iri
        """,
        (list(terms),),
    ).fetchall()
    distribution = {str(row["term_iri"]): int(row["occurrences"]) for row in rows}
    total = sum(distribution.values())
    index = 1 - max(distribution.values()) / total if total else 0.0
    incident = connection.execute(
        "SELECT COUNT(*) AS count FROM semantic_incidents WHERE detector_type = 'DET-005'"
    ).fetchone()
    threshold = float(config["fragmentation_threshold"])
    assert incident is not None
    expected_detection = index > threshold
    observed_detection = int(incident["count"]) > 0
    return {
        "concept_group": "products-chemistry-2.0",
        "distribution": distribution,
        "fragmentation_index": round(index, 4),
        "threshold": threshold,
        "expected_detection": expected_detection,
        "observed_detection": observed_detection,
        "pass": expected_detection == observed_detection,
    }


def _traceability(connection: psycopg.Connection[dict[str, Any]]) -> dict[str, object]:
    incidents = connection.execute(
        """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE jsonb_array_length(evidence_references) > 0) AS linked
        FROM semantic_incidents
        """
    ).fetchone()
    evidence = connection.execute(
        """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE jsonb_array_length(evidence_references) > 0) AS linked,
               COUNT(*) FILTER (WHERE occurrence_count > 1) AS recurrent,
               COUNT(*) FILTER (WHERE organisation_count > 1) AS cross_org,
               COUNT(*) FILTER (WHERE jsonb_array_length(affected_concepts) > 0) AS coherent,
               COUNT(*) FILTER (WHERE recommendation ILIKE 'Review%%') AS actionable
        FROM evidence_candidates
        """
    ).fetchone()
    assert incidents is not None and evidence is not None
    incident_total, evidence_total = int(incidents["total"]), int(evidence["total"])
    return {
        "incidents": {
            "total": incident_total,
            "with_provenance": int(incidents["linked"]),
            "pass": incident_total > 0 and int(incidents["linked"]) == incident_total,
        },
        "evidence": {
            "total": evidence_total,
            "with_provenance": int(evidence["linked"]),
            "recurrent": int(evidence["recurrent"]),
            "cross_organisation": int(evidence["cross_org"]),
            "affected_concepts_present": int(evidence["coherent"]),
            "human_review_recommendation": int(evidence["actionable"]),
            "pass": evidence_total > 0
            and all(
                int(evidence[field]) == evidence_total
                for field in ("linked", "recurrent", "coherent", "actionable")
            ),
            "semantic_coherence": "manual review required",
        },
    }


def _json_url(path: str, base_url: str = "http://localhost:8000") -> Any:
    with urlopen(f"{base_url}{path}", timeout=180) as response:
        return json.load(response)


def _api_benchmark(base_url: str) -> dict[str, dict[str, float]]:
    endpoints = (
        "/api/v1/ecosystem/summary",
        "/api/v1/metrics",
        "/api/v1/validation/constraints?limit=25",
        "/api/v1/incidents?limit=100",
        "/api/v1/evidence?limit=100",
    )
    results: dict[str, dict[str, float]] = {}
    for endpoint in endpoints:
        samples: list[float] = []
        for _ in range(3):
            started = perf_counter()
            _json_url(endpoint, base_url)
            samples.append((perf_counter() - started) * 1000)
        samples.sort()
        results[endpoint] = {
            "minimum_ms": round(samples[0], 2),
            "median_ms": round(samples[1], 2),
            "maximum_ms": round(samples[2], 2),
        }
    return results


def _scale_benchmark() -> dict[str, dict[str, float | int]]:
    scenario = load_scenario()
    results: dict[str, dict[str, float | int]] = {}
    with tempfile.TemporaryDirectory(prefix="dpp-evaluation-") as directory:
        root = Path(directory)
        for count in (1_000, 10_000, 25_000):
            output = root / str(count)
            started = perf_counter()
            generate(replace(scenario, documents=count), output)
            generation_seconds = perf_counter() - started
            started = perf_counter()
            parsed = 0
            with (output / "documents.jsonl").open(encoding="utf-8") as lines:
                for line in lines:
                    json.loads(line)
                    parsed += 1
            parsing_seconds = perf_counter() - started
            results[str(count)] = {
                "documents": parsed,
                "generation_seconds": round(generation_seconds, 4),
                "generation_documents_per_second": round(count / generation_seconds, 1),
                "jsonl_parsing_seconds": round(parsing_seconds, 4),
                "jsonl_documents_per_second": round(count / parsing_seconds, 1),
            }
    return results


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Semantic Observatory Evaluation",
        "",
        f"Generated: {report['generated_at']}",
        f"Overall result: **{report['status']}**",
        "",
        "## Detector accuracy",
        "",
        "| Detector family | Precision | Recall | F1 | False positives | False negatives |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, result in report["detector_accuracy"].items():
        lines.append(
            f"| {name} | {result['precision']:.4f} | {result['recall']:.4f} | "
            f"{result['f1']:.4f} | {result['false_positive']} | {result['false_negative']} |"
        )
    lines.extend((
        "",
        "## Metric validity",
        "",
        "| Metric | Expected | Observed | Result |",
        "| --- | ---: | ---: | --- |",
    ))
    for name, result in report["metric_validity"].items():
        lines.append(
            f"| {name} | {result['expected']:.4f} | {result['observed']:.4f} | "
            f"{'PASS' if result['pass'] else 'FAIL'} |"
        )
    lines.extend((
        "",
        "## Scale and latency",
        "",
        (
            "The report contains measured 1k/10k/25k generation and JSONL parsing throughput, "
            "plus three-sample API latency. It makes no unmeasured validation-throughput claim."
        ),
        "",
        "## Evidence governance",
        "",
        (
            "Evidence quality is checked for recurrence, affected concepts, actionable "
            "human-review language, and provenance. Normative standard changes remain a "
            "human decision."
        ),
        "",
    ))
    return "\n".join(lines)


def evaluate(
    truth_path: Path = DEFAULT_TRUTH,
    summary_path: Path = DEFAULT_SUMMARY,
    base_url: str = "http://localhost:8000",
) -> dict[str, Any]:
    truth = _truth(truth_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with _connect() as connection:
        observed = _document_sets(connection)
        accuracy = {
            name: classification(truth[name], observed[name])
            for name in ("unknown_term", "deprecated_term", "mapping_gap", "legacy_version")
        }
        metric_checks = _metric_checks(connection, summary)
        fragmentation = _fragmentation(connection)
        traceability = _traceability(connection)
        signal_events = connection.execute(
            "SELECT COUNT(*) AS observations, SUM(occurrence_count) AS occurrences "
            "FROM semantic_observations"
        ).fetchone()
    assert signal_events is not None
    incident_trace = cast(dict[str, object], traceability["incidents"])
    evidence_trace = cast(dict[str, object], traceability["evidence"])
    passed = (
        all(result["f1"] == 1.0 for result in accuracy.values())
        and all(result["pass"] for result in metric_checks.values())
        and bool(fragmentation["pass"])
        and bool(incident_trace["pass"])
        and bool(evidence_trace["pass"])
    )
    return {
        "evaluation_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "scenario": summary["scenario"],
        "seed": summary["seed"],
        "documents": summary["documents"],
        "status": "PASS" if passed else "FAIL",
        "detector_accuracy": accuracy,
        "fragmentation_detection": fragmentation,
        "metric_validity": metric_checks,
        "traceability_and_evidence": traceability,
        "telemetry_volume": {
            "observations": int(signal_events["observations"]),
            "occurrences": int(signal_events["occurrences"]),
        },
        "scale_benchmark": _scale_benchmark(),
        "api_latency": _api_benchmark(base_url),
        "limitations": [
            "Validation throughput was not re-measured at 25k; no claim is made for it.",
            "Semantic coherence remains a manual evidence-review rubric item.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the semantic observatory MVP.")
    parser.add_argument("--truth", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    report = evaluate(args.truth, args.summary, args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(report), encoding="utf-8")
    print(f"Observatory evaluation {report['status']}: {args.output}")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
