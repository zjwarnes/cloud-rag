"""
Shared utilities for text processing and cost estimation.
"""

import re
from typing import List, Dict, Tuple


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 100) -> List[Dict[str, any]]:
    """Split text into overlapping chunks."""
    chunks = []
    step = chunk_size - overlap

    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size]
        if len(chunk.strip()) > 50:  # Skip very short chunks
            chunks.append({"text": chunk, "start": i, "end": min(i + chunk_size, len(text))})

    return chunks


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove control characters
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
    return text.strip()


def estimate_tokens(text: str) -> int:
    """Rough estimate of tokens (1 token ≈ 4 characters)."""
    return max(1, len(text) // 4)


def estimate_embedding_cost(num_tokens: int, model: str = "text-embedding-3-small") -> float:
    """Estimate cost of embeddings."""
    prices = {
        "text-embedding-3-small": 0.02 / 1_000_000,
        "text-embedding-3-large": 0.13 / 1_000_000,
    }
    return num_tokens * prices.get(model, 0.02 / 1_000_000)


def estimate_llm_cost(
    input_tokens: int, output_tokens: int, model: str = "gpt-4-turbo-preview"
) -> Tuple[float, float, float]:
    """Estimate LLM cost. Returns (input_cost, output_cost, total_cost)."""
    prices = {
        "gpt-4-turbo-preview": (10 / 1_000_000, 30 / 1_000_000),
        "gpt-4": (10 / 1_000_000, 30 / 1_000_000),
        "gpt-3.5-turbo": (0.5 / 1_000_000, 1.5 / 1_000_000),
    }

    input_price, output_price = prices.get(model, (10 / 1_000_000, 30 / 1_000_000))
    input_cost = input_tokens * input_price
    output_cost = output_tokens * output_price

    return input_cost, output_cost, input_cost + output_cost
