"""
SupportPilot AI — Response Evaluator Agent
Scores the quality of a generated support response before it goes to the customer.
"""

import json
from dataclasses import dataclass

from app.core.logger import get_logger
from app.ai.providers.base import LLMProvider, Message, CompletionOptions

logger = get_logger(__name__)

_EVALUATOR_SYSTEM_PROMPT = """You are a quality assurance specialist for customer support responses.
Evaluate the given response and return a JSON object with:
- "overall_score": float 0-1 (1 = excellent)
- "accuracy_score": float 0-1 (factually correct based on context)
- "empathy_score": float 0-1 (tone is empathetic and professional)
- "completeness_score": float 0-1 (addresses the customer's issue fully)
- "conciseness_score": float 0-1 (not too long, not too short)
- "issues": list of strings describing specific problems (empty if none)
- "suggestions": list of strings with improvement suggestions
- "is_safe_to_send": boolean (true if response meets quality threshold)

Quality threshold for is_safe_to_send: overall_score >= 0.7 AND no critical accuracy issues.

Return ONLY valid JSON."""


@dataclass
class EvaluationResult:
    overall_score: float
    accuracy_score: float
    empathy_score: float
    completeness_score: float
    conciseness_score: float
    issues: list[str]
    suggestions: list[str]
    is_safe_to_send: bool


class EvaluatorAgent:
    """
    Evaluates the quality of a generated support response.
    Acts as an automated QA gate before responses reach customers.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def evaluate(
        self,
        ticket_subject: str,
        ticket_description: str,
        generated_response: str,
        context: str,
    ) -> EvaluationResult:
        """
        Score a generated response across multiple quality dimensions.

        Args:
            ticket_subject:      Original ticket subject
            ticket_description:  Original ticket description
            generated_response:  The AI-generated response to evaluate
            context:             The RAG context used to generate the response

        Returns:
            EvaluationResult with scores and actionable feedback
        """
        evaluation_prompt = (
            f"ORIGINAL TICKET:\n"
            f"Subject: {ticket_subject}\n"
            f"Description: {ticket_description}\n\n"
            f"KNOWLEDGE BASE CONTEXT AVAILABLE:\n{context[:2000]}\n\n"
            f"GENERATED RESPONSE TO EVALUATE:\n{generated_response}\n\n"
            f"Evaluate the response quality."
        )

        result = await self.llm.complete(
            messages=[
                Message(role="system", content=_EVALUATOR_SYSTEM_PROMPT),
                Message(role="user", content=evaluation_prompt),
            ],
            options=CompletionOptions(temperature=0.1, max_tokens=1024),
        )

        try:
            parsed = json.loads(result.content.strip())
            evaluation = EvaluationResult(
                overall_score=float(parsed.get("overall_score", 0.5)),
                accuracy_score=float(parsed.get("accuracy_score", 0.5)),
                empathy_score=float(parsed.get("empathy_score", 0.5)),
                completeness_score=float(parsed.get("completeness_score", 0.5)),
                conciseness_score=float(parsed.get("conciseness_score", 0.5)),
                issues=parsed.get("issues", []),
                suggestions=parsed.get("suggestions", []),
                is_safe_to_send=bool(parsed.get("is_safe_to_send", False)),
            )
            logger.info(
                "response_evaluated",
                overall_score=evaluation.overall_score,
                is_safe_to_send=evaluation.is_safe_to_send,
            )
            return evaluation

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("evaluation_parse_error", error=str(e))
            return EvaluationResult(
                overall_score=0.0,
                accuracy_score=0.0,
                empathy_score=0.0,
                completeness_score=0.0,
                conciseness_score=0.0,
                issues=["Evaluation parsing failed"],
                suggestions=["Manual review required"],
                is_safe_to_send=False,
            )
