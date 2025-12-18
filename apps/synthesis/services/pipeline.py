"""Synthesis service for response generation."""

import sys
import os
import logging
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.models import (
    SynthesisRequest,
    SynthesisResponse,
    Citation,
    RetrievalRequest,
    RetrievedChunk,
)
from common.utils import estimate_llm_cost, estimate_tokens

logger = logging.getLogger(__name__)


class LLMService:
    """Interface with OpenAI LLM."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> tuple[str, int]:
        """Generate response from LLM."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        text = response.choices[0].message.content
        tokens = response.usage.completion_tokens

        return text, tokens


class PromptBuilder:
    """Build prompts for LLM."""

    @staticmethod
    def build_system_prompt() -> str:
        """Build system prompt."""
        return """You are a helpful assistant that answers questions based on provided documents.

IMPORTANT:
1. Answer based ONLY on the provided context
2. If information is not in context, say "I don't have that information"
3. Be concise and accurate
4. Cite sources when appropriate"""

    @staticmethod
    def build_user_prompt(query: str, context: str) -> str:
        """Build user prompt."""
        return f"""Based on the following context, answer the question.

CONTEXT:
{context}

QUESTION:
{query}

Provide a direct answer with citations to the source documents."""


class SynthesisPipeline:
    """Main synthesis pipeline."""

    def __init__(self, openai_api_key: str):
        self.llm = LLMService(openai_api_key)
        self.prompt_builder = PromptBuilder()

    def synthesize(self, request: SynthesisRequest) -> SynthesisResponse:
        """Execute synthesis pipeline."""
        import time

        start = time.time()

        try:
            # 1. Check if we have chunks
            if not request.retrieval_result.chunks:
                logger.warning("No chunks retrieved")
                return SynthesisResponse(
                    answer="I don't have relevant information to answer your question.",
                    citations=[],
                    synthesis_latency_ms=(time.time() - start) * 1000,
                    tokens_used=0,
                    cost_estimate=0.0,
                )

            # 2. Assemble context
            context_text = self._assemble_context(request.retrieval_result.chunks)

            # 3. Build prompts
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(request.query, context_text)

            # 4. Generate
            logger.info("Generating response")
            answer, tokens_out = self.llm.generate(
                system_prompt,
                user_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            # 5. Build citations
            citations = self._build_citations(request.retrieval_result.chunks)

            # 6. Calculate costs
            tokens_in = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
            _, _, cost = estimate_llm_cost(tokens_in, tokens_out)

            latency_ms = (time.time() - start) * 1000

            return SynthesisResponse(
                answer=answer,
                citations=citations,
                synthesis_latency_ms=latency_ms,
                tokens_used=tokens_in + tokens_out,
                cost_estimate=cost,
            )

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            raise

    def _assemble_context(self, chunks: List[RetrievedChunk], max_tokens: int = 2000) -> str:
        """Assemble context from chunks."""
        context_parts = []
        current_tokens = 0

        for chunk in chunks:
            chunk_tokens = estimate_tokens(chunk.text)
            if current_tokens + chunk_tokens <= max_tokens:
                source_line = f"[Source: {chunk.source_url}"
                if chunk.page:
                    source_line += f" (page {chunk.page})"
                source_line += "]"

                context_parts.append(f"{source_line}\n{chunk.text}")
                current_tokens += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    def _build_citations(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        """Build citation list."""
        citations = []
        for chunk in chunks:
            citation = Citation(
                chunk_id=chunk.id,
                doc_id=chunk.doc_id,
                source_url=chunk.source_url,
                page=chunk.page,
                text_preview=chunk.text[:100],
            )
            citations.append(citation)
        return citations
