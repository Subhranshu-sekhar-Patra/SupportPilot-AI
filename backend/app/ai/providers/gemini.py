"""
SupportPilot AI — Google Gemini LLM Provider Implementation
"""

from typing import AsyncIterator

from tenacity import retry, stop_after_attempt, wait_exponential
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

from app.core.logger import get_logger
from app.ai.providers.base import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
    Message,
)
from app.config import settings
from app.core.exceptions import AIProviderError

logger = get_logger(__name__)

# Default options for Gemini
_DEFAULT_OPTIONS = CompletionOptions(temperature=0.3, max_tokens=2048)


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation of LLMProvider.
    Uses the google-generativeai SDK.
    API key is read from settings (never hardcoded).
    """

    def __init__(
        self,
        model: str = settings.default_model,
        embedding_model: str = settings.default_embedding_model,
    ):
        self.model_name = model
        self.embedding_model_name = embedding_model

        # Configure the SDK if available
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
        opts = options or _DEFAULT_OPTIONS
        try:
            # Build Gemini-compatible contents list
            contents = self._messages_to_contents(messages)

            generation_config = genai.types.GenerationConfig(
                temperature=opts.temperature,
                max_output_tokens=opts.max_tokens,
                top_p=opts.top_p,
                stop_sequences=opts.stop_sequences or None,
            )

            response = await self._model.generate_content_async(
                contents=contents,
                generation_config=generation_config,
            )

            if not response.text:
                raise AIProviderError("Gemini returned empty response")

            usage = response.usage_metadata
            return CompletionResult(
                content=response.text,
                model=self.model_name,
                input_tokens=getattr(usage, "prompt_token_count", 0),
                output_tokens=getattr(usage, "candidates_token_count", 0),
            )

        except AIProviderError:
            raise
        except Exception as e:
            logger.error("gemini_completion_error", error=str(e))
            raise AIProviderError(f"Gemini completion failed: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens from Gemini."""
        opts = options or _DEFAULT_OPTIONS
        try:
            contents = self._messages_to_contents(messages)
            generation_config = genai.types.GenerationConfig(
                temperature=opts.temperature,
                max_output_tokens=opts.max_tokens,
            )

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


def get_llm_provider() -> LLMProvider:
    """
    Factory that returns the configured LLM provider.
    Extend this to support multiple providers based on settings.
    """
    if settings.default_ai_provider == "gemini":
        return GeminiProvider()
    raise ValueError(f"Unsupported AI provider: {settings.default_ai_provider}")
