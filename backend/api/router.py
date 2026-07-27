from fastapi import APIRouter

import backend.api.documents_endpoint as documents_endpoint
import backend.api.search_endpoint as search_endpoint

router = APIRouter()

router.include_router(search_endpoint.router, prefix="/api", tags=["search"])
router.include_router(
    documents_endpoint.router,
    prefix="/api",
    tags=["documents"],
)
