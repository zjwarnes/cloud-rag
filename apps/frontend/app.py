"""Frontend app main entry point."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from handlers.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Frontend Service", description="Frontend for RAG queries", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "RAG Frontend Service"}


@app.on_event("startup")
async def startup():
    logger.info("Frontend service starting up")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Frontend service shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
