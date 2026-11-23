"""
SupportPilot AI — Google Gemini LLM Provider Implementation
"""

import json
from typing import AsyncIterator
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    try:
        from google import genai
        HAS_GENAI = True
    except ImportError:
        genai = None
        HAS_GENAI = False

from app.ai.providers.base import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
    Message,
)
from app.ai.providers.mock import MockLLMProvider
from app.config import settings
from app.core.exceptions import AIProviderError
from app.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_OPTIONS = CompletionOptions(temperature=0.2, max_tokens=2048)


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation of LLMProvider.
    Uses google-generativeai SDK.
    API key is read securely from settings (never hardcoded).
    """

    def __init__(
        self,
        model: str = settings.default_model,
        embedding_model: str = settings.default_embedding_model,
    ):
        self.model_name = model
        self.embedding_model_name = embedding_model

        if HAS_GENAI and settings.gemini_api_key and genai is not None:
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self._model = genai.GenerativeModel(model_name=self.model_name)
            except Exception as e:
                logger.warning("gemini_configure_deferred", reason=str(e))
                self._model = None
        else:
            self._model = None

        logger.info(
            "gemini_provider_initialized",
            model=self.model_name,
            embedding_model=self.embedding_model_name,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> CompletionResult:
        """Generate a completion using Gemini."""
        if not self._model:
            raise AIProviderError("Gemini provider is not configured. Check GEMINI_API_KEY.")

        opts = options or _DEFAULT_OPTIONS
        try:
            contents = self._messages_to_contents(messages)

            generation_config = {
                "temperature": opts.temperature,
                "max_output_tokens": opts.max_tokens,
                "top_p": opts.top_p,
            }
            if opts.response_mime_type:
                generation_config["response_mime_type"] = opts.response_mime_type

            response = await self._model.generate_content_async(
                contents=contents,
                generation_config=generation_config,
            )

            if not response.text:
                raise AIProviderError("Gemini returned empty response")

            usage = getattr(response, "usage_metadata", None)
            return CompletionResult(
                content=response.text,
                model=self.model_name,
                input_tokens=getattr(usage, "prompt_token_count", 0),
                output_tokens=getattr(usage, "candidates_token_count", 0),
            )

        except AIProviderError:
            raise
        except Exception as e:
            err_msg = str(e)
            if "ResourceExhausted" in err_msg or "429" in err_msg:
                logger.error("gemini_quota_exhausted", error=err_msg)
                raise AIProviderError(f"Gemini API quota exhausted: {err_msg}") from e
            logger.error("gemini_completion_error", error=err_msg)
            raise AIProviderError(f"Gemini completion failed: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens from Gemini."""
        if not self._model:
            raise AIProviderError("Gemini provider is not configured.")

        opts = options or _DEFAULT_OPTIONS
        try:
            contents = self._messages_to_contents(messages)
            generation_config = {
                "temperature": opts.temperature,
                "max_output_tokens": opts.max_tokens,
            }

            response = await self._model.generate_content_async(
                contents=contents,
                generation_config=generation_config,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error("gemini_stream_error", error=str(e))
            raise AIProviderError(f"Gemini streaming failed: {e}") from e

    async def embed(self, text: str) -> list[float]:
        """Generate a single embedding vector using Gemini."""
        try:
            result = genai.embed_content(
                model=self.embedding_model_name,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            logger.error("gemini_embed_error", error=str(e))
            raise AIProviderError(f"Gemini embedding failed: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]

    @staticmethod
    def _messages_to_contents(messages: list[Message]) -> list[dict]:
        """
        Convert our Message format to Gemini's contents list.
        System messages are prepended as a user turn.
        """
        contents = []
        system_parts = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "user":
                parts = []
                if system_parts:
                    parts.extend(system_parts)
                    system_parts = []
                parts.append(msg.content)
                contents.append({"role": "user", "parts": parts})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [msg.content]})

        return contents


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """
    Factory that returns the configured LLM provider.
    Defaults to Gemini if configured, or MockLLMProvider for offline/test environments.
    """
    provider = provider_name or settings.default_ai_provider

    if provider == "mock":
        return MockLLMProvider()

    if provider == "gemini":
        if settings.gemini_api_key:
            return GeminiProvider()
        logger.info("gemini_key_missing_falling_back_to_mock")
        return MockLLMProvider()

    raise ValueError(f"Unsupported AI provider: {provider}")
