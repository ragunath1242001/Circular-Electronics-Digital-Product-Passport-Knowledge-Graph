from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db.governance import get_report, get_report_rows, list_audit_logs, list_reports
from app.schemas.governance import AuditLog, ReportJob, ReportRequest
from app.services.graph_store import GraphStoreError
from app.services.report_service import generate_report, render_csv

router = APIRouter(prefix="/api/v1", tags=["reports", "governance"])


@router.post("/reports", response_model=ReportJob, status_code=status.HTTP_201_CREATED)
def post_report(request: ReportRequest) -> ReportJob:
    try:
        return generate_report(request.report_type)
    except (psycopg.Error, GraphStoreError) as exc:
        raise HTTPException(status_code=503, detail="The report could not be generated.") from exc


@router.get("/reports", response_model=list[ReportJob])
def reports(limit: int = Query(default=50, ge=1, le=200)) -> list[ReportJob]:
    try:
        return list_reports(limit)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Report history is unavailable.") from exc


@router.get("/reports/{report_id}", response_model=ReportJob)
def report(report_id: UUID) -> ReportJob:
    try:
        result = get_report(report_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Report metadata is unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return result


@router.get("/reports/{report_id}/download")
def download_report(report_id: UUID) -> Response:
    stored_report = report(report_id)
    try:
        rows = get_report_rows(report_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Report export is unavailable.") from exc
    assert rows is not None
    filename = f"{stored_report.report_type}-{stored_report.generated_at:%Y%m%d-%H%M%S}.csv"
    return Response(
        render_csv(rows, stored_report.sources), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit-logs", response_model=list[AuditLog])
def audit_logs(limit: int = Query(default=100, ge=1, le=500)) -> list[AuditLog]:
    try:
        return list_audit_logs(limit)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Audit history is unavailable.") from exc
