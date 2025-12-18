"""Ingestion service for handling PDF upload and embedding."""

import sys
import os
import uuid
import logging
from typing import List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.utils import chunk_text, clean_text, estimate_tokens, estimate_embedding_cost
from common.models import IngestResponse
from apps.ingestion.config import settings

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF files."""

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from PDF."""
        try:
            import PyPDF2

            text = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text.append(f"[Page {page_num + 1}]\n{page_text}")
            return "\n".join(text)
        except ImportError:
            logger.error("PyPDF2 not installed")
            raise
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            raise


class EmbeddingService:
    """Generate embeddings for chunks."""

    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.batch_size = settings.embedding_batch_size

    def embed_texts(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        """Generate embeddings with batching."""
        embeddings = []
        total_tokens = 0

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            response = self.client.embeddings.create(model=self.model, input=batch)
            embeddings.extend([item.embedding for item in response.data])

            # Estimate tokens
            for text in batch:
                total_tokens += estimate_tokens(text)

        logger.info(f"Generated {len(embeddings)} embeddings ({total_tokens} tokens)")
        return embeddings, total_tokens


class VectorStoreService:
    """Store embeddings in Pinecone."""

    def __init__(self):
        self.pc = None
        self.index = None

    def _ensure_connected(self):
        """Lazy initialization of Pinecone connection."""
        if self.index is None:
            from pinecone import Pinecone

            self.pc = Pinecone(api_key=settings.pinecone_api_key)
            self.index = self.pc.Index(settings.pinecone_index_name)

    def upsert_vectors(
        self,
        doc_id: str,
        chunks: List[dict],
        embeddings: List[List[float]],
        user_id: str = "default",
    ) -> int:
        """Store vectors in Pinecone."""
        self._ensure_connected()
        import time

        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{doc_id}_chunk_{i}"
            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "doc_id": doc_id,
                        "source_url": (
                            f"gs://{settings.gcs_bucket_name}/{doc_id}/document.pdf"
                            if settings.gcs_bucket_name
                            else ""
                        ),
                        "page": chunk.get("page", 0),
                        "chunk_index": i,
                        "text": chunk["text"],
                        "user_id": user_id,
                        "created_at": time.time(),
                    },
                }
            )

        # Batch upsert
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self.index.upsert(vectors=batch)

        logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
        return len(vectors)


class IngestionPipeline:
    """Main ingestion pipeline."""

    def __init__(self):
        self.extractor = PDFExtractor()
        self.embedder = EmbeddingService()
        self.vector_store = VectorStoreService()

    def ingest(
        self, file_path: str, user_id: str = "default", chunk_size: int = None, overlap: int = None
    ) -> IngestResponse:
        """Ingest a PDF document."""
        doc_id = str(uuid.uuid4())
        chunk_size = chunk_size or settings.chunk_size
        overlap = overlap or settings.chunk_overlap

        try:
            # 1. Extract
            logger.info(f"Extracting text from {file_path}")
            text = self.extractor.extract_text(file_path)
            text = clean_text(text)

            # 2. Chunk
            logger.info("Chunking text")
            chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

            if not chunks:
                return IngestResponse(
                    status="error",
                    doc_id=doc_id,
                    chunks_created=0,
                    embedding_tokens=0,
                    cost_estimate=0.0,
                    message="No chunks created",
                )

            # 3. Embed
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings, tokens = self.embedder.embed_texts([c["text"] for c in chunks])
            embedding_cost = estimate_embedding_cost(tokens, settings.openai_embedding_model)

            # 4. Store
            logger.info("Storing in vector database")
            self.vector_store.upsert_vectors(doc_id, chunks, embeddings, user_id)

            return IngestResponse(
                status="complete",
                doc_id=doc_id,
                chunks_created=len(chunks),
                embedding_tokens=tokens,
                cost_estimate=embedding_cost,
                message=f"Ingested {len(chunks)} chunks",
            )

        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            return IngestResponse(
                status="error",
                doc_id=doc_id,
                chunks_created=0,
                embedding_tokens=0,
                cost_estimate=0.0,
                message=str(e),
            )
