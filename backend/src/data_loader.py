from pathlib import Path

from langchain_community.document_loaders import (
    CSVLoader,
    PyPDFLoader,
    TextLoader,
)


def load_document(file_path: str, document_id: str, original_name: str):
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        documents = PyPDFLoader(str(path)).load()
    elif suffix == ".txt":
        documents = TextLoader(str(path), encoding="utf-8").load()
    elif suffix == ".csv":
        documents = CSVLoader(str(path)).load()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    for document in documents:
        document.metadata.update(
            {
                "document_id": document_id,
                "filename": original_name,
                "source": str(path),
            }
        )

    return documents
