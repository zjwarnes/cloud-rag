"""Retrieval API handlers."""

import sys
import os
import uuid
import logging
from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.models import RetrievalRequest, RetrievalResult
from common.metrics import get_collector, Timer
from services.pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["retrieval"])

pipeline = RetrievalPipeline()
metrics = get_collector("retrieval")


@router.post("/retrieve", response_model=RetrievalResult)
async def retrieve(request: RetrievalRequest) -> RetrievalResult:
    """Retrieve relevant chunks for a query."""
    query_id = str(uuid.uuid4())

    with Timer() as timer:
        try:
            result = pipeline.retrieve(request)
            metrics.record(query_id, timer.elapsed_ms, success=True)
            return result

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            metrics.record(query_id, timer.elapsed_ms, success=False, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "retrieval"}
