"""Frontend API handlers."""

import sys
import os
import uuid
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.models import FrontendRequest, SynthesisRequest, RetrievalResult
import httpx
import json
from typing import AsyncGenerator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["frontend"])

from apps.frontend.config import settings


async def stream_synthesis_response(
    query: str, user_id: str = "default"
) -> AsyncGenerator[str, None]:
    """Stream synthesis response as SSE."""
    query_id = str(uuid.uuid4())

    try:
        # Call synthesis service
        async with httpx.AsyncClient() as client:
            synthesis_request = SynthesisRequest(
                query=query,
                user_id=user_id,
                retrieval_result=RetrievalResult(
                    query=query, chunks=[], retrieval_latency_ms=0, num_chunks_searched=0
                ),
            )

            response = await client.post(
                f"{settings.synthesis_service_url}/api/v1/synthesize",
                json=synthesis_request.model_dump(exclude={"retrieval_result"}),
                timeout=60.0,
            )
            response.raise_for_status()

            result = response.json()

            # Stream answer as tokens
            yield f"event: answer\ndata: {json.dumps({'text': result['answer']})}\n\n"

            # Stream citations
            for citation in result.get("citations", []):
                yield f"event: citation\ndata: {json.dumps(citation)}\n\n"

            # Final metadata
            metadata = {
                "latency_ms": result["synthesis_latency_ms"],
                "cost": result["cost_estimate"],
                "tokens": result["tokens_used"],
            }
            yield f"event: done\ndata: {json.dumps(metadata)}\n\n"

    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.post("/query")
async def query(request: FrontendRequest):
    """Query endpoint (returns SSE stream)."""
    return StreamingResponse(
        stream_synthesis_response(request.query, request.user_id), media_type="text/event-stream"
    )


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "frontend"}
