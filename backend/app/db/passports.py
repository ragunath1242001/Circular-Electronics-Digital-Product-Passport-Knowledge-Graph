from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.schemas.ingestion import SmartphoneRecord
from app.schemas.passports import Passport, PassportVersion, Product

SCHEMA_SQL = (
    Path(__file__).resolve().parents[2] / "migrations" / "003_passports.sql"
).read_text(encoding="utf-8")
PRODUCT_META = "id, created_at, updated_at, archived_at"
PASSPORT_COLUMNS = "id, product_id, current_version, status, created_at, updated_at, archived_at"


def _connect() -> psycopg.Connection[dict[str, Any]]:
    settings = get_settings()
    connection = psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        row_factory=dict_row,
    )
    connection.execute(SCHEMA_SQL)
    return connection


def _product(row: dict[str, Any]) -> Product:
    metadata = {key: row[key] for key in PRODUCT_META.split(", ")}
    return Product.model_validate({**row["data"], **metadata})


def create_product(record: SmartphoneRecord) -> Product:
    with _connect() as connection:
        row = connection.execute(
            f"""
            INSERT INTO products (id, identifier, data)
            VALUES (%s, %s, %s)
            RETURNING data, {PRODUCT_META}
            """,
            (uuid4(), record.product_identifier, Jsonb(record.model_dump(mode="json"))),
        ).fetchone()
    assert row is not None
    return _product(row)


def list_products(include_archived: bool = False, limit: int = 50) -> list[Product]:
    archived_filter = "" if include_archived else "WHERE archived_at IS NULL"
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT data, {PRODUCT_META} FROM products {archived_filter} "
            "ORDER BY created_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [_product(row) for row in rows]


def get_product(product_id: UUID) -> Product | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT data, {PRODUCT_META} FROM products WHERE id = %s",
            (product_id,),
        ).fetchone()
    return _product(row) if row else None


def update_product(product_id: UUID, record: SmartphoneRecord) -> Product | None:
    with _connect() as connection:
        row = connection.execute(
            f"""
            UPDATE products SET identifier = %s, data = %s, updated_at = NOW()
            WHERE id = %s AND archived_at IS NULL
            RETURNING data, {PRODUCT_META}
            """,
            (record.product_identifier, Jsonb(record.model_dump(mode="json")), product_id),
        ).fetchone()
    return _product(row) if row else None


def archive_product(product_id: UUID) -> bool:
    with _connect() as connection:
        row = connection.execute(
            """
            UPDATE products SET archived_at = NOW(), updated_at = NOW()
            WHERE id = %s AND archived_at IS NULL RETURNING id
            """,
            (product_id,),
        ).fetchone()
        if row:
            connection.execute(
                """
                UPDATE passports SET status = 'ARCHIVED', archived_at = NOW(), updated_at = NOW()
                WHERE product_id = %s AND status = 'ACTIVE'
                """,
                (product_id,),
            )
    return row is not None


def create_passport(passport_id: UUID, product_id: UUID, graph_uri: str) -> Passport:
    with _connect() as connection:
        row = connection.execute(
            f"""
            INSERT INTO passports (id, product_id) VALUES (%s, %s)
            RETURNING {PASSPORT_COLUMNS}
            """,
            (passport_id, product_id),
        ).fetchone()
        connection.execute(
            "INSERT INTO passport_versions (passport_id, version, graph_uri) VALUES (%s, 1, %s)",
            (passport_id, graph_uri),
        )
    assert row is not None
    return Passport.model_validate(row)


def list_passports(include_archived: bool = False, limit: int = 50) -> list[Passport]:
    archived_filter = "" if include_archived else "WHERE status = 'ACTIVE'"
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT {PASSPORT_COLUMNS} FROM passports {archived_filter} "
            "ORDER BY created_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [Passport.model_validate(row) for row in rows]


def get_passport(passport_id: UUID) -> Passport | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT {PASSPORT_COLUMNS} FROM passports WHERE id = %s",
            (passport_id,),
        ).fetchone()
    return Passport.model_validate(row) if row else None


def get_product_passport(product_id: UUID) -> Passport | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT {PASSPORT_COLUMNS} FROM passports WHERE product_id = %s",
            (product_id,),
        ).fetchone()
    return Passport.model_validate(row) if row else None


def add_passport_version(passport_id: UUID, version: int, graph_uri: str) -> Passport | None:
    # ponytail: optimistic insert; add retry/locking when concurrent passport editors exist.
    with _connect() as connection:
        row = connection.execute(
            f"""
            UPDATE passports SET current_version = %s, updated_at = NOW()
            WHERE id = %s AND status = 'ACTIVE' AND current_version = %s
            RETURNING {PASSPORT_COLUMNS}
            """,
            (version, passport_id, version - 1),
        ).fetchone()
        if row:
            connection.execute(
                """
                INSERT INTO passport_versions (passport_id, version, graph_uri)
                VALUES (%s, %s, %s)
                """,
                (passport_id, version, graph_uri),
            )
    return Passport.model_validate(row) if row else None


def get_passport_version(passport_id: UUID, version: int | None = None) -> PassportVersion | None:
    clause = "p.current_version" if version is None else "%s"
    params: tuple[object, ...] = (passport_id,) if version is None else (passport_id, version)
    with _connect() as connection:
        row = connection.execute(
            f"""
            SELECT v.passport_id, v.version, v.graph_uri, v.created_at
            FROM passport_versions v JOIN passports p ON p.id = v.passport_id
            WHERE v.passport_id = %s AND v.version = {clause}
            """,
            params,
        ).fetchone()
    return PassportVersion.model_validate(row) if row else None


def list_passport_versions(passport_id: UUID) -> list[PassportVersion]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT passport_id, version, graph_uri, created_at
            FROM passport_versions WHERE passport_id = %s ORDER BY version DESC
            """,
            (passport_id,),
        ).fetchall()
    return [PassportVersion.model_validate(row) for row in rows]


def archive_passport(passport_id: UUID) -> bool:
    with _connect() as connection:
        row = connection.execute(
            """
            UPDATE passports SET status = 'ARCHIVED', archived_at = NOW(), updated_at = NOW()
            WHERE id = %s AND status = 'ACTIVE' RETURNING id
            """,
            (passport_id,),
        ).fetchone()
    return row is not None
