"""
SupportPilot AI — Response Generator Agent
Generates a helpful, empathetic support response using retrieved context.
"""

from dataclasses import dataclass

from app.core.logger import get_logger
from app.ai.providers.base import LLMProvider, Message, CompletionOptions

logger = get_logger(__name__)

_GENERATOR_SYSTEM_PROMPT = """You are a helpful, empathetic, and professional customer support specialist.
Your job is to draft a response to a customer support ticket.

GUIDELINES:
- Be concise but complete (aim for 150-300 words)
- Start with empathy, then provide actionable solutions
- Use the provided knowledge base context to answer accurately
- If the context doesn't cover the issue fully, acknowledge that and offer escalation
- Do not make up facts or policies not found in the context
- Maintain a professional but friendly tone
- End with an offer for further assistance

You will receive:
1. The customer's ticket details
2. Relevant knowledge base context
"""


@dataclass
class GeneratedResponse:
    response_text: str
    model_used: str
    input_tokens: int
    output_tokens: int
    context_sources: list[str]


class GeneratorAgent:
    """
    Generates a draft support response using RAG context.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_response(
        self,
        subject: str,
        description: str,
        context: str,
        source_documents: list[str],
        customer_name: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> GeneratedResponse:
        """
        Generate a response to a support ticket.

        Args:
            subject:              Ticket subject
            description:          Ticket description
            context:              Formatted RAG context from retriever
            source_documents:     List of source document titles
            customer_name:        Customer's name (for personalization)
            conversation_history: Prior messages in this ticket

        Returns:
            GeneratedResponse with the draft response text
        """
        greeting = f"Dear {customer_name}," if customer_name else "Dear Customer,"

        user_prompt = (
            f"CUSTOMER TICKET:\n"
            f"Subject: {subject}\n"
            f"Description: {description}\n\n"
            f"{context}\n\n"
            f"Please draft a response. Start with: '{greeting}'"
        )

        # Build conversation history context if available
        messages: list[Message] = [
            Message(role="system", content=_GENERATOR_SYSTEM_PROMPT),
        ]

        # Include up to 3 prior messages for context
        if conversation_history:
            for msg in conversation_history[-3:]:
                messages.append(Message(
                    role="user" if msg.get("author_type") == "customer" else "assistant",
                    content=msg.get("content", ""),
                ))

        messages.append(Message(role="user", content=user_prompt))

        result = await self.llm.complete(
            messages,
            options=CompletionOptions(temperature=0.4, max_tokens=1024),
        )

        logger.info(
            "response_generated",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            sources=source_documents,
        )

        return GeneratedResponse(
            response_text=result.content.strip(),
            model_used=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            context_sources=source_documents,
        )
