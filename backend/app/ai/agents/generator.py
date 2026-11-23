"""
SupportPilot AI — Response Generation Agent
Generates strictly grounded customer support responses with inline document citations.
Never invents company policies or makes unsupported promises.
"""

from app.ai.providers.base import CompletionOptions, LLMProvider, Message
from app.core.logger import get_logger
from app.schemas.ai import GenerationOutput, RetrievalAssessment

logger = get_logger(__name__)

_GENERATOR_SYSTEM_PROMPT = """You are SupportPilot AI, an expert enterprise customer support assistant.
Your absolute mandate is ACCURACY and STRICT GROUNDING.

STRICT GROUNDING RULES:
1. SOURCE OF TRUTH: Use ONLY the provided Knowledge Base Context as your factual source of truth.
2. ZERO FABRICATION: NEVER invent company policies, warranty windows, refund terms, pricing, or service guarantees.
3. INLINE CITATIONS: For every factual claim or policy stated, you MUST include an inline citation in the exact format:
   [Doc: <Document Title> #<chunk_number>].
4. MISSING INFORMATION: If the provided Knowledge Base Context does NOT contain the answer, explicitly state that you do not have the complete policy on file and that a human support specialist will verify and assist them.
5. EMPATHY & PROFESSIONALISM: Maintain a courteous, calm, empathetic, and professional tone.
6. NO UNSUPPORTED PROMISES: Never promise discounts, exceptions, or specific timelines unless explicitly written in the context.

Output your response matching the GenerationOutput schema:
- "response_text": The customer-facing reply with greetings, actionable guidance, and inline citations.
- "confidence_score": float 0.0 to 1.0 representing confidence in answer groundedness.
- "citations": list of strings citing the document titles used (e.g. ["Acme Refund Policy #0"]).
- "has_missing_info": boolean (true if context was incomplete).
- "unanswered_questions": list of customer questions that couldn't be confirmed by context.
- "suggested_action": "reply_to_customer" or "escalate_to_human".
"""


class GeneratorAgent:
    """
    Generates verified, grounded responses for customer tickets.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_response(
        self,
        subject: str,
        description: str,
        retrieval: RetrievalAssessment,
        customer_name: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> GenerationOutput:
        """
        Draft a response using strictly grounded knowledge base context.
        """
        greeting_name = customer_name if customer_name else "Valued Customer"

        # Build prompt
        prompt_parts = [
            f"CUSTOMER TICKET:",
            f"Customer Name: {greeting_name}",
            f"Subject: {subject}",
            f"Inquiry: {description}\n",
        ]

        if conversation_history:
            history_lines = [
                f"{m.get('author_type', 'user').upper()}: {m.get('content', '')}"
                for m in conversation_history[-4:]
            ]
            prompt_parts.append("CONVERSATION THREAD HISTORY:\n" + "\n".join(history_lines) + "\n")

        prompt_parts.append(f"AUTHORITATIVE KNOWLEDGE BASE CONTEXT:\n{retrieval.formatted_context}\n")
        prompt_parts.append(
            f"INSTRUCTIONS:\n"
            f"Draft a response addressed to {greeting_name}. "
            f"Include inline citations [Doc: <title> #<chunk>] for all facts. "
            f"If context is missing or insufficient, state that a human agent will assist."
        )

        user_content = "\n".join(prompt_parts)

        messages = [
            Message(role="system", content=_GENERATOR_SYSTEM_PROMPT),
            Message(role="user", content=user_content),
        ]

        try:
            output = await self.llm.complete_structured(
                messages,
                response_model=GenerationOutput,
                options=CompletionOptions(temperature=0.2, max_tokens=1024),
            )
            logger.info(
                "response_generated",
                citations_count=len(output.citations),
                confidence=output.confidence_score,
                missing_info=output.has_missing_info,
            )
            return output

        except Exception as e:
            logger.error("generation_error_fallback", error=str(e))
            # Safe grounded fallback
            return GenerationOutput(
                response_text=(
                    f"Hello {greeting_name},\n\n"
                    f"Thank you for contacting our customer support team regarding '{subject}'. "
                    f"To ensure you receive the most accurate assistance, I have forwarded your ticket "
                    f"to a support specialist who will review your details and follow up promptly.\n\n"
                    f"Best regards,\nCustomer Support Team"
                ),
                confidence_score=0.4,
                citations=[],
                has_missing_info=True,
                unanswered_questions=[description[:100]],
                suggested_action="escalate_to_human",
            )
