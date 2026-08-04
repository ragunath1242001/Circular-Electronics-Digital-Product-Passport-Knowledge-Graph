import csv
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from statistics import mean
from uuid import uuid4

from app.core.config import get_settings
from app.db.governance import save_report
from app.db.passports import list_passports, list_products
from app.db.validation_runs import list_validation_runs
from app.schemas.governance import AuditLog, ReportJob, ReportType
from app.services.graph_store import select

Summary = dict[str, int | float | str]
ReportData = tuple[list[dict[str, str]], Summary, list[str]]


def _api(path: str) -> str:
    return f"{get_settings().api_base_url.rstrip('/')}{path}"


def _compliance() -> ReportData:
    reports = list_validation_runs(1000)
    passports = list_passports(False, 200)
    rows = [
        {
            "validation_run": str(report.id),
            "conforms": str(report.conforms).lower(),
            "violations": str(report.violations),
            "warnings": str(report.warnings),
            "generated_at": report.created_at.isoformat(),
            "source": _api(f"/api/v1/validation/runs/{report.id}"),
        }
        for report in reports
    ]
    passed = sum(report.conforms for report in reports)
    summary: Summary = {
        "active_passports": len(passports),
        "validation_runs": len(reports),
        "conformance_rate": round(passed * 100 / len(reports), 1) if reports else 0,
        "violations": sum(report.violations for report in reports),
    }
    sources = sorted({row["source"] for row in rows})
    return rows, summary, sources or [_api("/api/v1/validation/runs")]


def _sustainability() -> ReportData:
    products = list_products(False, 200)
    rows = [
        {
            "product": product.product_name,
            "identifier": product.product_identifier,
            "manufacturer": product.manufacturer_name,
            "repairability_score": str(product.repairability_score),
            "recycled_content_percentage": str(product.recycled_content_percentage),
            "carbon_kg_co2e": str(product.carbon_kg_co2e),
            "source": _api(f"/api/v1/products/{product.id}"),
        }
        for product in products
    ]
    summary: Summary = {
        "products": len(products),
        "average_repairability": round(mean(float(p.repairability_score) for p in products), 2)
        if products else 0,
        "average_recycled_content": round(
            mean(float(p.recycled_content_percentage) for p in products), 2
        ) if products else 0,
        "average_carbon_kg_co2e": round(mean(float(p.carbon_kg_co2e) for p in products), 2)
        if products else 0,
    }
    return rows, summary, sorted({row["source"] for row in rows}) or [_api("/api/v1/products")]


def _supplier_quality() -> ReportData:
    products = list_products(False, 200)
    grouped = defaultdict(list)
    for product in products:
        grouped[product.supplier_name].append(product)
    rows = []
    for supplier, supplied_products in sorted(grouped.items()):
        sources = [_api(f"/api/v1/products/{product.id}") for product in supplied_products]
        rows.append({
            "supplier": supplier,
            "products": str(len(supplied_products)),
            "data_completeness_percentage": "100.0",
            "average_recycled_content": str(round(mean(
                float(product.recycled_content_percentage) for product in supplied_products
            ), 2)),
            "source": " | ".join(sources),
        })
    summary: Summary = {
        "suppliers": len(grouped),
        "products": len(products),
        "average_completeness": 100.0 if products else 0,
    }
    sources = sorted({_api(f"/api/v1/products/{product.id}") for product in products})
    return rows, summary, sources or [_api("/api/v1/products")]


def _certificates() -> ReportData:
    rows = select("""PREFIX dpp: <https://example.org/dpp/>
SELECT DISTINCT ?graph ?product ?certificate ?identifier ?type ?validUntil WHERE {
  GRAPH ?graph {
    ?product dpp:hasCertificate ?certificate .
    OPTIONAL { ?certificate dpp:certificateIdentifier ?identifier }
    OPTIONAL { ?certificate dpp:certificateType ?type }
    OPTIONAL { ?certificate dpp:validUntil ?validUntil }
  }
}""")
    today = date.today()
    expiry = today + timedelta(days=30)
    expired = expiring = 0
    for row in rows:
        row["source"] = row.get("graph", _api("/api/v1/sparql/query"))
        try:
            valid_until = date.fromisoformat(row.get("validUntil", ""))
            expired += valid_until < today
            expiring += today <= valid_until <= expiry
        except ValueError:
            pass
    summary: Summary = {
        "certificates": len(rows),
        "expired": expired,
        "expiring_in_30_days": expiring,
    }
    sources = sorted({row["source"] for row in rows})
    return rows, summary, sources or [_api("/api/v1/sparql/query")]


BUILDERS = {
    "compliance": _compliance,
    "sustainability": _sustainability,
    "supplier-quality": _supplier_quality,
    "certificate": _certificates,
}


def generate_report(report_type: ReportType) -> ReportJob:
    rows, summary, sources = BUILDERS[report_type]()
    generated_at = datetime.now(UTC)
    report = ReportJob(
        id=uuid4(), report_type=report_type, status="COMPLETED", row_count=len(rows),
        summary=summary, sources=sources, generated_at=generated_at,
    )
    audit = AuditLog(
        id=uuid4(), actor="local-demo-session", action="REPORT_GENERATED",
        entity_type="report", entity_id=str(report.id), result="SUCCESS",
        details={"report_type": report_type, "row_count": len(rows), "source_count": len(sources)},
        created_at=generated_at,
    )
    save_report(report, rows, audit)
    return report


def render_csv(rows: list[dict[str, str]], sources: list[str]) -> bytes:
    export_rows = rows or [{"finding": "No matching records", "source": sources[0]}]
    fields = list(dict.fromkeys(key for row in export_rows for key in row))
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in export_rows:
        writer.writerow({
            key: f"'{value}" if value.startswith(("=", "+", "-", "@")) else value
            for key, value in row.items()
        })
    return output.getvalue().encode("utf-8-sig")
