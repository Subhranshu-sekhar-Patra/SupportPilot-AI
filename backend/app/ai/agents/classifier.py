"""
SupportPilot AI — Query Classification Agent
Classifies customer intent, urgency, sentiment, and flags immediate human escalation triggers.
"""

from app.ai.providers.base import CompletionOptions, LLMProvider, Message
from app.core.logger import get_logger
from app.schemas.ai import ClassificationOutput, CustomerSentiment, TicketCategory, TicketUrgency

logger = get_logger(__name__)

_CLASSIFIER_SYSTEM_PROMPT = """You are an expert customer support classification intelligence agent for SupportPilot AI.
Analyze the incoming customer ticket and output a structured JSON evaluation matching this exact schema:
- "category": one of ["billing", "technical", "account", "feature_request", "bug_report", "general_inquiry", "security", "compliance"]
- "priority": one of ["low", "medium", "high", "urgent"]
- "sentiment": one of ["positive", "neutral", "negative", "frustrated", "angry"]
- "urgency_score": float 0.0 to 1.0 (1.0 = immediate emergency / outage / legal threat)
- "requires_immediate_human": boolean. Must be true if:
    * The customer is extremely angry, cursing, or threatening legal action/lawsuit.
    * The customer explicitly demands a human agent, manager, or supervisor.
    * The ticket involves a critical security vulnerability or compliance breach.
- "confidence": float 0.0 to 1.0
- "summary": 1-sentence concise description of the customer request.
- "reasoning": 1-2 sentence justification for this classification.

Return ONLY valid JSON matching the schema. No markdown formatting.
"""


class ClassifierAgent:
    """
    Classifies support tickets and customer messages using the provider abstraction.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def classify(
        self,
        subject: str,
        description: str,
        conversation_history: list[dict] | None = None,
    ) -> ClassificationOutput:
        """
        Classify a customer support ticket.
        """
        history_context = ""
        if conversation_history:
            history_lines = [
                f"{m.get('author_type', 'user').upper()}: {m.get('content', '')[:150]}"
                for m in conversation_history[-3:]
            ]
            history_context = "\nRecent Conversation:\n" + "\n".join(history_lines)

        user_content = (
            f"Ticket Subject: {subject}\n"
            f"Ticket Description: {description}"
            f"{history_context}"
        )

        messages = [
            Message(role="system", content=_CLASSIFIER_SYSTEM_PROMPT),
            Message(role="user", content=user_content),
        ]

        try:
            output = await self.llm.complete_structured(
                messages,
                response_model=ClassificationOutput,
                options=CompletionOptions(temperature=0.1, max_tokens=512),
            )
            logger.info(
                "ticket_classified",
                category=output.category.value,
                priority=output.priority.value,
                sentiment=output.sentiment.value,
                requires_human=output.requires_immediate_human,
                confidence=output.confidence,
            )
            return output

        except Exception as e:
            logger.warning("classification_fallback_triggered", error=str(e))
            # Rule-based fallback if model fails
            lower_desc = (subject + " " + description).lower()
            is_urgent = any(w in lower_desc for w in ["urgent", "lawyer", "sue", "manager", "human", "furious"])
            return ClassificationOutput(
                category=TicketCategory.GENERAL_INQUIRY,
                priority=TicketUrgency.URGENT if is_urgent else TicketUrgency.MEDIUM,
                sentiment=CustomerSentiment.ANGRY if is_urgent else CustomerSentiment.NEUTRAL,
                urgency_score=0.9 if is_urgent else 0.5,
                requires_immediate_human=is_urgent,
                confidence=0.6,
                summary=subject[:100],
                reasoning=f"Fallback classification applied due to model error: {e}",
            )
