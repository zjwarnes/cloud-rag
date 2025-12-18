"""Ingestion API handlers."""

import sys
import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.models import IngestRequest, IngestResponse
from common.metrics import get_collector, Timer
import tempfile
from services.pipeline import IngestionPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["ingest"])

pipeline = IngestionPipeline()
metrics = get_collector("ingestion")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...), user_id: str = "default"):
    """Ingest a PDF document."""
    query_id = str(uuid.uuid4())

    with Timer() as timer:
        try:
            # Save temporarily
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = os.path.join(temp_dir, file.filename)
                contents = await file.read()
                with open(temp_path, "wb") as f:
                    f.write(contents)

                # Ingest
                result = pipeline.ingest(temp_path, user_id=user_id)

            metrics.record(query_id, timer.elapsed_ms, success=True)
            return result

        except Exception as e:
            logger.error(f"Ingest error: {e}")
            metrics.record(query_id, timer.elapsed_ms, success=False, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "service": "ingestion"}
