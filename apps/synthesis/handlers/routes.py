"""Synthesis API handlers."""

import sys
import os
import uuid
import logging
from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.models import SynthesisRequest, SynthesisResponse, RetrievalRequest
from common.metrics import get_collector, Timer
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["synthesis"])
metrics = get_collector("synthesis")

# Import config to get settings
from config import settings


@router.post("/synthesize", response_model=SynthesisResponse)
async def synthesize(request: SynthesisRequest) -> SynthesisResponse:
    """Synthesize response based on query and retrieval."""
    query_id = str(uuid.uuid4())

    with Timer() as timer:
        try:
            # Import here to avoid circular imports
            from services.pipeline import SynthesisPipeline

            # Call retrieval service
            logger.info("Calling retrieval service")
            async with httpx.AsyncClient() as client:
                retrieval_request = RetrievalRequest(
                    query=request.query, user_id=request.user_id, top_k=5  # Default
                )

                retrieval_response = await client.post(
                    f"{settings.retrieval_service_url}/api/v1/retrieve",
                    json=retrieval_request.model_dump(),
                    timeout=30.0,
                )
                retrieval_response.raise_for_status()

                from common.models import RetrievalResult

                retrieval_result = RetrievalResult(**retrieval_response.json())

            # Execute synthesis
            request.retrieval_result = retrieval_result

            pipeline = SynthesisPipeline(settings.openai_api_key)
            result = pipeline.synthesize(request)

            metrics.record(query_id, timer.elapsed_ms, success=True)
            return result

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            metrics.record(query_id, timer.elapsed_ms, success=False, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "synthesis"}
