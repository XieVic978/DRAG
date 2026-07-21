from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.search import RAGSearch

router = APIRouter()

rag_search = RAGSearch()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
def search(request: SearchRequest):
    try:
        answer = rag_search.search_and_summarize(
            request.query,
            top_k=request.top_k,
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
