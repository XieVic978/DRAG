import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.api.dependencies import rag_service
from backend.db import (
    delete_document_record,
    get_document,
    get_ready_document_by_hash,
    insert_document,
    list_documents,
    update_document_status,
)
from backend.src.data_loader import SUPPORTED_EXTENSIONS, load_document

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "backend" / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_FILES_PER_REQUEST = 50
WRITE_CHUNK_SIZE = 1024 * 1024


def _safe_original_name(filename: str | None) -> str:
    if not filename:
        return "unnamed"
    return Path(filename.replace("\\", "/")).name


@router.get("/documents")
def get_documents():
    return {
        "documents": list_documents(),
        "indexed_chunk_count": rag_service.vectorstore.count(),
    }


@router.post("/documents")
async def upload_documents(files: list[UploadFile] = File(...)):
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Upload at most {MAX_FILES_PER_REQUEST} files per request.",
        )

    results = []
    for uploaded_file in files:
        original_name = _safe_original_name(uploaded_file.filename)
        suffix = Path(original_name).suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            results.append(
                {
                    "filename": original_name,
                    "status": "failed",
                    "error": (
                        f"Unsupported file type '{suffix or 'unknown'}'. "
                        "Use PDF, TXT, or CSV."
                    ),
                }
            )
            await uploaded_file.close()
            continue

        document_id = str(uuid.uuid4())
        stored_path = UPLOAD_DIR / f"{document_id}{suffix}"
        file_hash = hashlib.sha256()
        total_size = 0
        indexed = False

        try:
            with stored_path.open("wb") as destination:
                while chunk := await uploaded_file.read(WRITE_CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > MAX_FILE_SIZE:
                        raise ValueError("File is larger than the 20 MB limit.")
                    file_hash.update(chunk)
                    destination.write(chunk)

            if total_size == 0:
                raise ValueError("The file is empty.")

            digest = file_hash.hexdigest()
            duplicate = get_ready_document_by_hash(digest)
            if duplicate:
                stored_path.unlink(missing_ok=True)
                results.append(
                    {
                        "document_id": duplicate["document_id"],
                        "filename": original_name,
                        "status": "duplicate",
                        "chunk_count": duplicate["chunk_count"],
                        "message": "This file is already in the document library.",
                    }
                )
                continue

            insert_document(
                document_id=document_id,
                filename=original_name,
                stored_path=str(stored_path),
                file_hash=digest,
                file_size=total_size,
                status="processing",
            )

            documents = load_document(
                str(stored_path),
                document_id,
                original_name,
            )
            chunk_count = rag_service.vectorstore.add_documents(documents)
            indexed = True
            update_document_status(
                document_id,
                "ready",
                chunk_count=chunk_count,
            )
            results.append(
                {
                    "document_id": document_id,
                    "filename": original_name,
                    "status": "ready",
                    "chunk_count": chunk_count,
                }
            )
        except Exception as error:
            if indexed:
                rag_service.vectorstore.delete_document(document_id)
            stored_path.unlink(missing_ok=True)
            existing_record = get_document(document_id)
            if existing_record:
                update_document_status(
                    document_id,
                    "failed",
                    error=str(error),
                )
            results.append(
                {
                    "document_id": document_id,
                    "filename": original_name,
                    "status": "failed",
                    "error": str(error),
                }
            )
        finally:
            await uploaded_file.close()

    return {"documents": results}


@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    document = get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        removed_chunks = rag_service.vectorstore.delete_document(document_id)
        Path(document["stored_path"]).unlink(missing_ok=True)
        delete_document_record(document_id)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {
        "document_id": document_id,
        "deleted": True,
        "removed_chunks": removed_chunks,
    }
