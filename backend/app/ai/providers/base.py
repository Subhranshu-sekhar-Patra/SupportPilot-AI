"""
SupportPilot AI — Abstract LLM Provider Interface
All AI providers must implement this interface.
This decouples business logic from any specific AI vendor.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Message:
    """A single message in a chat conversation."""
    role: str   # "user" | "assistant" | "system"
    content: str


@dataclass
class CompletionOptions:
    """Options controlling how the LLM generates text."""
    temperature: float = 0.3
    max_tokens: int = 2048
    top_p: float = 0.95
    stop_sequences: list[str] = field(default_factory=list)


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
    Implement this to add support for any AI backend (OpenAI, Gemini, Anthropic, etc.)
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> CompletionResult:
        """
        Generate a text completion from a list of messages.

        Args:
            messages: Conversation history / prompt
            options:  Generation parameters

        Returns:
            CompletionResult with generated text and usage metadata
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream a text completion token by token.

        Yields:
            Text chunks as they arrive from the provider
        """
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Text to embed

        Returns:
            Embedding as a list of floats
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single call.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (same order as input)
        """
        ...
