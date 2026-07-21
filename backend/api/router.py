from fastapi import APIRouter

import backend.api.search_endpoint as search_endpoint

router = APIRouter()

router.include_router(search_endpoint.router, prefix="/api", tags=["search"])
