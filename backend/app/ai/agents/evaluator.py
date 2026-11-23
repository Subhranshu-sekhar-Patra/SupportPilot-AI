"""
SupportPilot AI — Response Quality Evaluation Agent
Automated QA gatekeeper (LLM-as-a-Judge) that verifies groundedness,
hallucination absence, relevance, and policy compliance before sending.
"""

from app.ai.providers.base import CompletionOptions, LLMProvider, Message
from app.core.logger import get_logger
from app.schemas.ai import EvaluationReport, EvaluationVerdict, GenerationOutput, RetrievalAssessment

logger = get_logger(__name__)

_EVALUATOR_SYSTEM_PROMPT = """You are the Senior QA and Safety Evaluator Agent for SupportPilot AI.
Your job is to rigorously review the AI-generated support response against the Authoritative Knowledge Base Context and Customer Inquiry.

EVALUATION CRITERIA:
1. GROUNDEDNESS / FAITHFULNESS (0.0 to 1.0):
   - Is EVERY factual statement made in the response directly supported by the context?
   - If the response invents policies, refunds, discounts, or deadlines NOT in the context, GROUNDEDNESS MUST BE < 0.50 and "hallucination_detected" MUST BE TRUE.
2. RELEVANCE (0.0 to 1.0):
   - Does the response directly address the customer's problem or acknowledge questions appropriately?
3. TONE & POLITE COMPLIANCE (0.0 to 1.0):
   - Is the tone empathetic, respectful, and professional?
4. OVERALL SCORE (0.0 to 1.0):
   - Weighted average: 0.50 * groundedness + 0.35 * relevance + 0.15 * tone.
5. VERDICT:
   - "approve": overall_score >= 0.70 AND hallucination_detected is false AND no unsupported claims.
   - "escalate": overall_score < 0.70 OR hallucination_detected is true OR customer requested human.
   - "revise": response is mostly grounded but needs formatting or minor citation fix.

Output valid JSON matching the EvaluationReport schema.
"""


class EvaluatorAgent:
    """
    Evaluates response quality, detecting hallucinations and unsupported promises.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def evaluate(
        self,
        ticket_subject: str,
        ticket_description: str,
        retrieval: RetrievalAssessment,
        generation: GenerationOutput,
    ) -> EvaluationReport:
        """
        Evaluate the generated response against the source context.
        """
        user_prompt = (
            f"CUSTOMER INQUIRY:\n"
            f"Subject: {ticket_subject}\n"
            f"Description: {ticket_description}\n\n"
            f"AUTHORITATIVE KNOWLEDGE BASE CONTEXT:\n{retrieval.formatted_context[:2500]}\n\n"
            f"GENERATED AI RESPONSE TO EVALUATE:\n{generation.response_text}\n\n"
            f"Reported Citations: {generation.citations}\n"
            f"Missing Info Flag: {generation.has_missing_info}\n\n"
            f"Perform rigorous evaluation and output the EvaluationReport JSON."
        )

        messages = [
            Message(role="system", content=_EVALUATOR_SYSTEM_PROMPT),
            Message(role="user", content=user_prompt),
        ]

        try:
            report = await self.llm.complete_structured(
                messages,
                response_model=EvaluationReport,
                options=CompletionOptions(temperature=0.1, max_tokens=512),
            )

            # Extra programmatic safety guard: If hallucination detected, force ESCALATE
            if report.hallucination_detected or report.groundedness_score < 0.65:
                report.verdict = EvaluationVerdict.ESCALATE
                if not report.escalation_reason:
                    report.escalation_reason = "Groundedness failure or hallucination detected in generated response."

            logger.info(
                "response_evaluated",
                overall=report.overall_score,
                groundedness=report.groundedness_score,
                relevance=report.relevance_score,
                verdict=report.verdict.value,
                hallucination=report.hallucination_detected,
            )
            return report

        except Exception as e:
            logger.warning("evaluator_fallback_triggered", error=str(e))
            # Conservative safety fallback: route to human review
            return EvaluationReport(
                groundedness_score=0.5,
                relevance_score=0.5,
                tone_score=0.8,
                overall_score=0.55,
                hallucination_detected=False,
                unsupported_claims=["Evaluation model failed to verify response."],
                verdict=EvaluationVerdict.ESCALATE,
                escalation_reason=f"Evaluation safety gate triggered: {e}",
            )
