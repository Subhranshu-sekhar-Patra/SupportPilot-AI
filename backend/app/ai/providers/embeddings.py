"""
SupportPilot AI — Configurable Embedding Provider Architecture
Supports:
1. Google Gemini Embeddings (models/text-embedding-004)
2. Local Deterministic Vector Provider (768-dim normalized semantic vectors for offline/test environments)
"""

import math
import re
from abc import ABC, abstractmethod
from typing import Sequence

from app.config import settings
from app.core.exceptions import AIProviderError
from app.core.logger import get_logger

logger = get_logger(__name__)


class BaseEmbeddingProvider(ABC):
    """Abstract interface for text embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple text strings."""
        ...


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini Embedding implementation using text-embedding-004."""

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        self.model_name = model_name or settings.default_embedding_model
        self.api_key = api_key or settings.gemini_api_key
        self._dim = 768

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, text: str) -> list[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            response = genai.embed_content(
                model=self.model_name,
                content=list(texts),
                task_type="retrieval_document",
            )
            embeddings = response.get("embedding", [])
            # genai returns single vector if 1 text, or list of vectors if multiple
            if embeddings and isinstance(embeddings[0], (int, float)):
                return [embeddings]
            return embeddings
        except Exception as e:
            logger.error("gemini_embedding_failed", error=str(e))
            raise AIProviderError(f"Gemini embedding API call failed: {e}") from e


class LocalDeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """
    High-performance 768-dimensional normalized dense embedding generator.
    Produces deterministic semantic vectors from token & n-gram frequency distributions
    with L2-unit normalization.
    Ensures offline unit testing and development work out-of-the-box with zero API cost.
    """

    def __init__(self, dimension: int = 768):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _generate_vector(self, text: str) -> list[float]:
        tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
        vec = [0.0] * self._dim

        if not tokens:
            return vec

        # Project tokens & word bigrams into 768-dim space using consistent hashing
        for token in tokens:
            idx = abs(hash(token)) % self._dim
            vec[idx] += 1.0

            # Subword 3-grams
            for i in range(len(token) - 2):
                sub = token[i : i + 3]
                sub_idx = abs(hash(sub)) % self._dim
                vec[sub_idx] += 0.35

        # Word bigrams
        for i in range(len(tokens) - 1):
            bg = f"{tokens[i]}_{tokens[i+1]}"
            bg_idx = abs(hash(bg)) % self._dim
            vec[bg_idx] += 1.5

        # L2-unit normalization (so dot product equals cosine similarity)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]

        return vec

    async def embed(self, text: str) -> list[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]


def get_embedding_provider() -> BaseEmbeddingProvider:
    """
    Factory returning the configured embedding provider.
    Uses Gemini if GEMINI_API_KEY is configured; otherwise uses Local deterministic embeddings.
    """
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        logger.info("using_gemini_embedding_provider")
        return GeminiEmbeddingProvider()
    
    logger.info("using_local_deterministic_embedding_provider")
    return LocalDeterministicEmbeddingProvider()
