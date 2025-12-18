"""Retrieval service for vector search and ranking."""

import sys
import os
import logging
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.models import RetrievalRequest, RetrievalResult, RetrievedChunk
from apps.retrieval.config import settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Query vectors from Pinecone."""

    def __init__(self):
        from pinecone import Pinecone

        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index = self.pc.Index(settings.pinecone_index_name)

    def search(
        self, query_embedding: List[float], top_k: int = 5, user_id: str = "default"
    ) -> List[dict]:
        """Search for similar vectors."""
        try:
            filter_dict = {"user_id": {"$eq": user_id}}
            results = self.index.query(
                vector=query_embedding, top_k=top_k, include_metadata=True, filter=filter_dict
            )

            chunks = []
            for match in results.matches:
                chunk = {
                    "id": match.id,
                    "score": match.score,
                    "text": match.metadata.get("text", ""),
                    "doc_id": match.metadata.get("doc_id"),
                    "source_url": match.metadata.get("source_url"),
                    "page": match.metadata.get("page"),
                    "chunk_index": match.metadata.get("chunk_index"),
                }
                chunks.append(chunk)

            logger.info(f"Retrieved {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Search error: {e}")
            raise


class EmbeddingService:
    """Embed queries."""

    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model

    def embed_query(self, query: str) -> List[float]:
        """Embed a query."""
        response = self.client.embeddings.create(model=self.model, input=[query])
        return response.data[0].embedding


class RankingService:
    """Rank and filter retrieval results."""

    @staticmethod
    def rank_chunks(chunks: List[dict]) -> List[dict]:
        """Sort chunks by score."""
        return sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)

    @staticmethod
    def deduplicate_chunks(chunks: List[dict]) -> List[dict]:
        """Remove duplicate chunks."""
        seen = {}
        dedup = []

        for chunk in chunks:
            key = f"{chunk['doc_id']}_{chunk['chunk_index']}"
            if key not in seen:
                seen[key] = True
                dedup.append(chunk)

        return dedup


class RetrievalPipeline:
    """Main retrieval pipeline."""

    def __init__(self):
        self.search_service = VectorSearchService()
        self.embedding_service = EmbeddingService()
        self.ranking_service = RankingService()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Execute retrieval pipeline."""
        import time

        start = time.time()

        try:
            # 1. Embed query
            logger.info(f"Embedding query: {request.query}")
            query_embedding = self.embedding_service.embed_query(request.query)

            # 2. Search
            logger.info("Searching vectors")
            chunks = self.search_service.search(
                query_embedding, top_k=request.top_k, user_id=request.user_id
            )

            # 3. Deduplicate
            chunks = self.ranking_service.deduplicate_chunks(chunks)

            # 4. Rank
            chunks = self.ranking_service.rank_chunks(chunks)

            # Convert to RetrievedChunk models
            retrieved_chunks = [
                RetrievedChunk(
                    id=c["id"],
                    text=c["text"],
                    doc_id=c["doc_id"],
                    source_url=c["source_url"],
                    page=c.get("page"),
                    chunk_index=c["chunk_index"],
                    score=c["score"],
                )
                for c in chunks
            ]

            latency_ms = (time.time() - start) * 1000

            return RetrievalResult(
                query=request.query,
                chunks=retrieved_chunks,
                retrieval_latency_ms=latency_ms,
                num_chunks_searched=len(chunks),
            )

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            raise
