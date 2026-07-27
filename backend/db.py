import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "backend" / "data" / "documents.sqlite3"


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                status TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                uploaded_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_file_hash
            ON documents(file_hash)
            """
        )


def insert_document(
    document_id: str,
    filename: str,
    stored_path: str,
    file_hash: str,
    file_size: int,
    status: str = "processing",
) -> None:
    uploaded_at = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO documents (
                document_id,
                filename,
                stored_path,
                file_hash,
                file_size,
                status,
                uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                filename,
                stored_path,
                file_hash,
                file_size,
                status,
                uploaded_at,
            ),
        )


def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int = 0,
    error: str | None = None,
) -> None:
    with _connect() as connection:
        connection.execute(
            """
            UPDATE documents
            SET status = ?, chunk_count = ?, error = ?
            WHERE document_id = ?
            """,
            (status, chunk_count, error, document_id),
        )


def list_documents() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                document_id,
                filename,
                file_size,
                status,
                chunk_count,
                error,
                uploaded_at
            FROM documents
            ORDER BY uploaded_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(document_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()
    return dict(row) if row else None


def get_ready_document_by_hash(file_hash: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT * FROM documents
            WHERE file_hash = ? AND status = 'ready'
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (file_hash,),
        ).fetchone()
    return dict(row) if row else None


def delete_document_record(document_id: str) -> None:
    with _connect() as connection:
        connection.execute(
            "DELETE FROM documents WHERE document_id = ?",
            (document_id,),
        )
