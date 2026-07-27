import os
import pickle
from pathlib import Path
from threading import RLock
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from backend.src.embedding import EmbeddingPipeline


class FaissVectorStore:
    def __init__(
        self,
        persist_dir: str = "faiss_store",
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.index = None
        self.metadata: list[dict[str, Any]] = []
        self.embedding_model = embedding_model
        self.model = SentenceTransformer(embedding_model)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._lock = RLock()
        print(f"[INFO] Loaded embedding model: {embedding_model}")

    @property
    def faiss_path(self) -> Path:
        return self.persist_dir / "faiss.index"

    @property
    def metadata_path(self) -> Path:
        return self.persist_dir / "metadata.pkl"

    def exists(self) -> bool:
        return self.faiss_path.exists() and self.metadata_path.exists()

    def count(self) -> int:
        with self._lock:
            return int(self.index.ntotal) if self.index is not None else 0

    def _prepare_documents(
        self,
        documents: list[Any],
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        pipeline = EmbeddingPipeline(
            model_name=self.embedding_model,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            model=self.model,
        )
        chunks = pipeline.chunk_documents(documents)
        if not chunks:
            raise ValueError("The document did not produce any searchable chunks")

        embeddings = np.asarray(
            pipeline.embed_chunks(chunks),
            dtype="float32",
        )
        metadatas = [
            {**chunk.metadata, "text": chunk.page_content}
            for chunk in chunks
        ]
        return embeddings, metadatas

    def build_from_documents(self, documents: list[Any]) -> int:
        """Replace the complete index with the supplied documents."""
        if not documents:
            raise ValueError("No documents found")

        embeddings, metadatas = self._prepare_documents(documents)
        with self._lock:
            self.index = faiss.IndexFlatL2(embeddings.shape[1])
            self.metadata = []
            self._add_embeddings_unlocked(embeddings, metadatas)
            self._save_unlocked()
        return len(metadatas)

    def add_documents(self, documents: list[Any]) -> int:
        """Chunk, embed, and append documents to the current index."""
        if not documents:
            raise ValueError("No documents to add")

        embeddings, metadatas = self._prepare_documents(documents)
        with self._lock:
            self._add_embeddings_unlocked(embeddings, metadatas)
            self._save_unlocked()
        return len(metadatas)

    def _add_embeddings_unlocked(
        self,
        embeddings: np.ndarray,
        metadatas: list[dict[str, Any]],
    ) -> None:
        if embeddings.ndim != 2 or embeddings.shape[0] == 0:
            raise ValueError("Embeddings must be a non-empty two-dimensional array")
        if embeddings.shape[0] != len(metadatas):
            raise ValueError("Every embedding must have one metadata record")

        if self.index is None:
            self.index = faiss.IndexFlatL2(embeddings.shape[1])
        elif self.index.d != embeddings.shape[1]:
            raise ValueError("Embedding dimensions do not match the saved index")

        self.index.add(embeddings)
        self.metadata.extend(metadatas)

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        if self.index is None:
            return

        temporary_index = self.faiss_path.with_suffix(".index.tmp")
        temporary_metadata = self.metadata_path.with_suffix(".pkl.tmp")

        faiss.write_index(self.index, str(temporary_index))
        with temporary_metadata.open("wb") as file:
            pickle.dump(self.metadata, file)

        os.replace(temporary_index, self.faiss_path)
        os.replace(temporary_metadata, self.metadata_path)

    def load(self) -> None:
        with self._lock:
            self.index = faiss.read_index(str(self.faiss_path))
            with self.metadata_path.open("rb") as file:
                self.metadata = pickle.load(file)

            if self.index.ntotal != len(self.metadata):
                raise ValueError(
                    "FAISS index and metadata are inconsistent: "
                    f"{self.index.ntotal} vectors but {len(self.metadata)} metadata rows"
                )
        print(f"[INFO] Loaded FAISS index and metadata from {self.persist_dir}")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if self.index is None or self.index.ntotal == 0:
                return []

            result_count = min(max(top_k, 1), self.index.ntotal)
            distances, indices = self.index.search(query_embedding, result_count)
            results = []
            for index_id, distance in zip(indices[0], distances[0]):
                if index_id < 0 or index_id >= len(self.metadata):
                    continue
                results.append(
                    {
                        "index": int(index_id),
                        "distance": float(distance),
                        "metadata": self.metadata[index_id],
                    }
                )
            return results

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_embedding = self.model.encode([query_text]).astype("float32")
        return self.search(query_embedding, top_k=top_k)

    def delete_document(self, document_id: str) -> int:
        """Remove every vector belonging to a document and rebuild the flat index."""
        with self._lock:
            if self.index is None or self.index.ntotal == 0:
                return 0

            remove_positions = [
                position
                for position, metadata in enumerate(self.metadata)
                if metadata.get("document_id") == document_id
            ]
            if not remove_positions:
                return 0

            remove_set = set(remove_positions)
            keep_positions = [
                position
                for position in range(len(self.metadata))
                if position not in remove_set
            ]

            if keep_positions:
                kept_embeddings = np.vstack(
                    [self.index.reconstruct(position) for position in keep_positions]
                ).astype("float32")
                kept_metadata = [self.metadata[position] for position in keep_positions]
                self.index = faiss.IndexFlatL2(kept_embeddings.shape[1])
                self.index.add(kept_embeddings)
                self.metadata = kept_metadata
            else:
                dimension = self.index.d
                self.index = faiss.IndexFlatL2(dimension)
                self.metadata = []

            self._save_unlocked()
            return len(remove_positions)
