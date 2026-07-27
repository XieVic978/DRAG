import os
from typing import Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from backend.src.vector_store import FaissVectorStore

load_dotenv()


class RAGSearch:
    def __init__(
        self,
        persist_dir: str = "faiss_store",
        embedding_model: str = "all-MiniLM-L6-v2",
        llm_model: str = "openai/gpt-oss-120b",
    ):
        self.vectorstore = FaissVectorStore(persist_dir, embedding_model)
        if self.vectorstore.exists():
            self.vectorstore.load()

        groq_api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=llm_model,
            temperature=0,
        )
        print(f"[INFO] Groq LLM initialized: {llm_model}")

    def search_and_answer(
        self,
        query: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        results = self.vectorstore.query(query, top_k=top_k)
        if not results:
            return {
                "answer": "Upload at least one document before asking a question.",
                "sources": [],
            }

        context_sections = []
        sources = []
        seen_sources = set()

        for number, result in enumerate(results, start=1):
            metadata = result["metadata"]
            text = metadata.get("text", "").strip()
            if not text:
                continue

            filename = metadata.get("filename") or os.path.basename(
                metadata.get("source", "Unknown document")
            )
            page = metadata.get("page")
            page_label = page + 1 if isinstance(page, int) else None
            context_sections.append(
                f"[Source {number}: {filename}"
                f"{f', page {page_label}' if page_label else ''}]\n{text}"
            )

            source_key = (metadata.get("document_id"), filename, page_label)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(
                    {
                        "document_id": metadata.get("document_id"),
                        "filename": filename,
                        "page": page_label,
                    }
                )

        if not context_sections:
            return {
                "answer": "The uploaded documents did not contain readable context.",
                "sources": [],
            }

        context = "\n\n".join(context_sections)
        prompt = f"""You answer questions using only the uploaded document excerpts below.

Rules:
- Answer the user's actual question, not merely summarize the excerpts.
- Do not use outside knowledge.
- If the excerpts do not contain enough information, say so clearly.
- Keep the answer direct and useful.
- Cite supporting excerpts inline using [Source 1], [Source 2], and so on.

Question:
{query}

Document excerpts:
{context}

Answer:"""
        response = self.llm.invoke(prompt)
        return {
            "answer": response.content,
            "sources": sources,
        }

    # Kept for compatibility with the original command-line example.
    def search_and_summarize(self, query: str, top_k: int = 5) -> str:
        return self.search_and_answer(query, top_k=top_k)["answer"]
