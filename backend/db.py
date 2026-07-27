import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "documents.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            status TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            error TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_document(document_id, filename, stored_path, status="processing"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO documents (document_id, filename, stored_path, status) VALUES (?, ?, ?, ?)",
        (document_id, filename, stored_path, status),
    )
    conn.commit()
    conn.close()


def update_document_status(document_id, status, chunk_count=0, error=None):
    conn = get_connection()
    conn.execute(
        "UPDATE documents SET status = ?, chunk_count = ?, error = ? WHERE document_id = ?",
        (status, chunk_count, error, document_id),
    )
    conn.commit()
    conn.close()


def list_documents():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents").fetchall()
    conn.close()
    return [dict(row) for row in rows]
