"""
SupportPilot AI — Abstract LLM Provider Interface
All AI providers must implement this interface.
This decouples business logic from any specific AI vendor (Gemini, OpenAI, Anthropic, Mock).
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Type, TypeVar
from pydantic import BaseModel, ValidationError

from app.core.exceptions import AIProviderError
from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class Message:
    """A single message in a chat conversation."""
    role: str   # "user" | "assistant" | "system"
    content: str


@dataclass
class CompletionOptions:
    """Options controlling how the LLM generates text."""
    temperature: float = 0.2
    max_tokens: int = 2048
    top_p: float = 0.95
    stop_sequences: list[str] = field(default_factory=list)
    response_mime_type: str | None = None  # e.g. "application/json"


@dataclass
class CompletionResult:
    """Result of a text completion call."""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Implement this to add support for any AI backend.
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> CompletionResult:
        """
        Generate a text completion from a list of messages.
        """
        ...

    async def complete_structured(
        self,
        messages: list[Message],
        response_model: Type[T],
        options: CompletionOptions | None = None,
    ) -> T:
        """
        Generate a completion and validate it against a Pydantic model.
        Extracts JSON even if enclosed in markdown code fences.
        """
        opts = options or CompletionOptions(temperature=0.1, response_mime_type="application/json")
        result = await self.complete(messages, opts)
        raw_text = result.content.strip()

        # Clean markdown code blocks if present
        if "```json" in raw_text:
            match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1).strip()
        elif "```" in raw_text:
            match = re.search(r"```\s*(.*?)\s*```", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1).strip()

        try:
            parsed_dict = json.loads(raw_text)
            return response_model.model_validate(parsed_dict)
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(
                "structured_completion_validation_error",
                error=str(err),
                raw_preview=raw_text[:200],
            )
            # Try finding first JSON object substring { ... }
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if json_match:
                try:
                    return response_model.model_validate(json.loads(json_match.group(0)))
                except Exception:
                    pass
            raise AIProviderError(
                f"Failed to parse model output into {response_model.__name__}: {err}"
            ) from err

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> AsyncIterator[str]:
        """Stream a text completion token by token."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...
