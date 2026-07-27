from backend.src.search import RAGSearch


# Search and upload routes must share the same in-memory FAISS index.
rag_service = RAGSearch()
