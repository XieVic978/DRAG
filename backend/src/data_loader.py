from pathlib import Path
from typing import Any

from langchain_community.document_loaders import (
    CSVLoader,
    PyPDFLoader,
    TextLoader,
)


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".csv"}


def load_document(
    file_path: str,
    document_id: str,
    original_name: str,
) -> list[Any]:
    """Load one uploaded file and attach metadata to every page/row."""
    path = Path(file_path).resolve()
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        documents = PyPDFLoader(str(path)).load()
    elif suffix == ".txt":
        documents = TextLoader(
            str(path),
            encoding="utf-8",
            autodetect_encoding=True,
        ).load()
    elif suffix == ".csv":
        documents = CSVLoader(str(path), autodetect_encoding=True).load()
    else:
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

    if not documents:
        raise ValueError("The file did not contain readable text")

    for document in documents:
        document.metadata.update(
            {
                "document_id": document_id,
                "filename": original_name,
                "source": str(path),
            }
        )

    return documents


def load_all_documents(data_dir: str) -> list[Any]:
    """
    Load all supported files from the data directory and convert to LangChain document structure.
    Supported: PDF, TXT, CSV
    """
    # Use project root data folder
    data_path = Path(data_dir).resolve()
    print(f"[DEBUG] Data path: {data_path}")
    documents = []

    # PDF files
    pdf_files = list(data_path.glob("**/*.pdf"))
    print(f"[DEBUG] Found {len(pdf_files)} PDF files: {[str(f) for f in pdf_files]}")
    for pdf_file in pdf_files:
        print(f"[DEBUG] Loading PDF: {pdf_file}")
        try:
            loader = PyPDFLoader(str(pdf_file))
            loaded = loader.load()
            print(f"[DEBUG] Loaded {len(loaded)} PDF docs from {pdf_file}")
            documents.extend(loaded)
        except Exception as e:
            print(f"[ERROR] Failed to load PDF {pdf_file}: {e}")

    # TXT Files
    txt_files = list(data_path.glob("**/*.txt"))
    print(f"[DEBUG] Found {len(txt_files)} TXT files: {[str(f) for f in txt_files]}")
    for txt_file in txt_files:
        print(f"[DEBUG] Loading TXT: {txt_file}")
        try:
            loader = TextLoader(str(txt_file))
            loaded = loader.load()
            print(f"[DEBUG] Loaded {len(loaded)} TXT docs from {txt_file}")
            documents.extend(loaded)
        except Exception as e:
            print(f"[ERROR] Failed to load TXT {txt_file} : {e}")

    # CSV Files
    csv_files = list(data_path.glob("**/*.csv"))
    print(f"[DEBUG] Found {len(csv_files)} CSV files: {[str(f) for f in csv_files]}")
    for csv_file in csv_files:
        print(f"[DEBUG] Loading CSV: {csv_file}")
        try:
            loader = CSVLoader(str(csv_file))
            loaded = loader.load()
            print(f"[DEBUG] Loaded {len(loaded)} CSV docs from {csv_file}")
            documents.extend(loaded)
        except Exception as e:
            print(f"[ERROR] Failed to load CSV {csv_file} : {e}")

    return documents


if __name__ == "__main__":
    docs = load_all_documents("backend/data")
    print(f"Loaded {len(docs)} documents.")
    print("Example document:", docs[0] if docs else None)
