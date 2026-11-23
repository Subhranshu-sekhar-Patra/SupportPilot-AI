"""
SupportPilot AI — Ticket Classification Agent
Categorizes support tickets and assigns priority using the LLM.
"""

import json
from dataclasses import dataclass

from app.core.logger import get_logger
from app.ai.providers.base import LLMProvider, Message, CompletionOptions

logger = get_logger(__name__)

_CLASSIFIER_SYSTEM_PROMPT = """You are a customer support ticket classification expert.
Analyze the provided ticket and return a JSON object with:
- "category": one of [billing, technical, account, feature_request, bug_report, general_inquiry, security, compliance]
- "priority": one of [low, medium, high, urgent]
- "sentiment": one of [positive, neutral, negative, angry]
- "confidence": float between 0 and 1
- "reasoning": brief explanation (1-2 sentences)

IMPORTANT: Return ONLY valid JSON — no markdown, no extra text.
"""


@dataclass
class ClassificationResult:
    category: str
    priority: str
    sentiment: str
    confidence: float
    reasoning: str


class ClassifierAgent:
    """
    Classifies a support ticket into a category and priority.
    Uses the abstract LLM provider — not tied to any specific model.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def classify(self, subject: str, description: str) -> ClassificationResult:
        """
        Classify a support ticket.

        Args:
            subject:     Ticket subject line
            description: Full ticket description

        Returns:
            ClassificationResult with category, priority, confidence, etc.
        """
        messages = [
            Message(role="system", content=_CLASSIFIER_SYSTEM_PROMPT),
            Message(
                role="user",
                content=(
                    f"Ticket Subject: {subject}\n\n"
                    f"Ticket Description:\n{description}"
                ),
            ),
        ]

        result = await self.llm.complete(
            messages,
            options=CompletionOptions(temperature=0.1, max_tokens=512),
        )

        try:
            parsed = json.loads(result.content.strip())
            classification = ClassificationResult(
                category=parsed.get("category", "general_inquiry"),
                priority=parsed.get("priority", "medium"),
                sentiment=parsed.get("sentiment", "neutral"),
                confidence=float(parsed.get("confidence", 0.5)),
                reasoning=parsed.get("reasoning", ""),
            )
            logger.info(
                "ticket_classified",
                category=classification.category,
                priority=classification.priority,
                confidence=classification.confidence,
            )
            return classification

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("classification_parse_error", raw=result.content, error=str(e))
            # Fallback defaults
            return ClassificationResult(
                category="general_inquiry",
                priority="medium",
                sentiment="neutral",
                confidence=0.0,
                reasoning="Classification failed — using defaults",
            )
