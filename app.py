from backend.src.data_loader import load_all_documents
from backend.src.search import RAGSearch
from backend.src.vector_store import FaissVectorStore

# Example usage
if __name__ == "__main__":
    docs = load_all_documents("backend/data")
    store = FaissVectorStore("faiss_store")
    store.build_from_documents(docs)
    store.load()
    print(store.query("is Cal Poly SLO an easy school to get accepted?", top_k=3))
    rag_search = RAGSearch()
    query = "is Cal Poly SLO an easy school to get accepted?"
    summary = rag_search.search_and_summarize(query, top_k=3)
    print("Summary:", summary)
