from fastapi import APIRouter, Depends

import db as database
from ..core.auth import require_api_key

router = APIRouter(prefix="/api", tags=["stats"], dependencies=[Depends(require_api_key)])


@router.get("/stats")
def get_stats():
    return database.get_stats()
