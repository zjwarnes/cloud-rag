"""Synthesis app main entry point."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from handlers.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Synthesis Service", description="Response synthesis and generation", version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    logger.info("Synthesis service starting up")


@app.on_event("shutdown")
async def shutdown():
    from common.metrics import get_collector

    metrics = get_collector("synthesis")
    metrics.log_summary()
    logger.info("Synthesis service shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
