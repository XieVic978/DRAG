from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.dependencies import rag_service

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/search")
def search(request: SearchRequest):
    try:
        return rag_service.search_and_answer(
            request.query.strip(),
            top_k=request.top_k,
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
