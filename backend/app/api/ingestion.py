import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.db.ingestion import get_ingestion_job, list_ingestion_errors, list_ingestion_jobs
from app.schemas.ingestion import IngestionError, IngestionJob
from app.services.graph_store import GraphStoreError
from app.services.ingestion_service import (
    IngestionFormatError,
    run_ingestion,
    run_semantic_ingestion,
)

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 2_000_000
MAX_JSONL_UPLOAD_BYTES = 25_000_000
FORMATS = {".csv": "csv", ".json": "json", ".jsonl": "jsonl"}
CONTENT_TYPES = {
    "csv": {"text/csv", "application/csv", "application/octet-stream"},
    "json": {"application/json", "application/octet-stream"},
    "jsonl": {"application/x-ndjson", "application/jsonl", "application/octet-stream"},
}


@router.post("/files", response_model=IngestionJob, status_code=status.HTTP_201_CREATED)
def ingest_file(
    file: Annotated[UploadFile, File()],
    source_system: Annotated[
        str,
        Form(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$"),
    ],
) -> IngestionJob:
    file_name = Path(file.filename or "upload").name
    data_format = FORMATS.get(Path(file_name).suffix.lower())
    if data_format is None:
        raise HTTPException(
            status_code=415,
            detail="Only .csv, .json, and .jsonl uploads are supported.",
        )
    if file.content_type not in CONTENT_TYPES[data_format]:
        raise HTTPException(
            status_code=415,
            detail=f"Invalid content type for {data_format} upload.",
        )
    try:
        if data_format == "jsonl":
            file.file.seek(0, 2)
            upload_size = file.file.tell()
            file.file.seek(0)
            if upload_size > MAX_JSONL_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="JSONL upload exceeds the 25 MB limit.")
            job = run_semantic_ingestion(file.file, source_system, file_name)
        else:
            raw_content = file.file.read(MAX_UPLOAD_BYTES + 1)
            if len(raw_content) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Upload exceeds the 2 MB limit.")
            try:
                content = raw_content.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=422,
                    detail="Upload must be UTF-8 encoded.",
                ) from exc
            job = run_ingestion(content, data_format, source_system, file_name)
    except IngestionFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except psycopg.Error as exc:
        logger.exception("ingestion_database_failed")
        raise HTTPException(status_code=503, detail="Ingestion metadata is unavailable.") from exc
    logger.info(
        "ingestion_completed",
        extra={"job_id": str(job.id), "action": "ingest", "result": job.status},
    )
    return job


@router.get("/jobs", response_model=list[IngestionJob])
def get_jobs(limit: int = Query(default=50, ge=1, le=200)) -> list[IngestionJob]:
    try:
        return list_ingestion_jobs(limit)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Ingestion jobs are unavailable.") from exc


@router.get("/jobs/{job_id}", response_model=IngestionJob)
def get_job(job_id: UUID) -> IngestionJob:
    try:
        job = get_ingestion_job(job_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Ingestion jobs are unavailable.") from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    return job


@router.get("/jobs/{job_id}/errors", response_model=list[IngestionError])
def get_job_errors(job_id: UUID) -> list[IngestionError]:
    try:
        if get_ingestion_job(job_id) is None:
            raise HTTPException(status_code=404, detail="Ingestion job not found.")
        return list_ingestion_errors(job_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Ingestion errors are unavailable.") from exc
