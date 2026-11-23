"""
SupportPilot AI — AI Agent Orchestrator
Coordinates Classify → Retrieve → Generate → Evaluate pipeline.
"""

from dataclasses import dataclass

from app.core.logger import get_logger
from app.ai.agents.classifier import ClassifierAgent, ClassificationResult
from app.ai.agents.retriever import RetrieverAgent, RetrievalContext
from app.ai.agents.generator import GeneratorAgent, GeneratedResponse
from app.ai.agents.evaluator import EvaluatorAgent, EvaluationResult
from app.ai.providers.gemini import get_llm_provider
from app.ai.rag.retrieval import RetrievalService

logger = get_logger(__name__)


@dataclass
class OrchestrationResult:
    """Full result of the AI pipeline for a single ticket."""
    classification: ClassificationResult
    context: RetrievalContext
    response: GeneratedResponse
    evaluation: EvaluationResult

    @property
    def ai_metadata(self) -> dict:
        """Serializable dict for storing in Ticket.ai_metadata column."""
        return {
            "classification": {
                "category": self.classification.category,
                "priority": self.classification.priority,
                "sentiment": self.classification.sentiment,
                "confidence": self.classification.confidence,
                "reasoning": self.classification.reasoning,
            },
            "retrieval": {
                "chunks_found": len(self.context.chunks),
                "source_documents": self.context.source_documents,
            },
            "generation": {
                "model_used": self.response.model_used,
                "input_tokens": self.response.input_tokens,
                "output_tokens": self.response.output_tokens,
            },
            "evaluation": {
                "overall_score": self.evaluation.overall_score,
                "is_safe_to_send": self.evaluation.is_safe_to_send,
                "issues": self.evaluation.issues,
            },
        }


class AgentOrchestrator:
    """
    Runs the full AI pipeline:
      1. Classify  — categorize and prioritize
      2. Retrieve  — find relevant KB articles (RAG)
      3. Generate  — draft a response
      4. Evaluate  — score the response quality

    Returns a complete OrchestrationResult.
    """

    def __init__(self, org_id: str):
        self.org_id = org_id
        llm = get_llm_provider()
        retrieval_service = RetrievalService(llm, org_id)

        self.classifier = ClassifierAgent(llm)
        self.retriever = RetrieverAgent(llm, retrieval_service)
        self.generator = GeneratorAgent(llm)
        self.evaluator = EvaluatorAgent(llm)

    async def process_ticket(
        self,
        ticket_id: str,
        subject: str,
        description: str,
        customer_name: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> OrchestrationResult:
        """
        Run the complete AI pipeline for a support ticket.

        Args:
            ticket_id:            Ticket DB ID (for logging)
            subject:              Ticket subject
            description:          Ticket description
            customer_name:        Optional customer name for personalization
            conversation_history: Prior messages for context

        Returns:
            OrchestrationResult with all pipeline outputs
        """
        logger.info("orchestration_started", ticket_id=ticket_id, org_id=self.org_id)

        # ── Step 1: Classify ───────────────────────────────
        classification = await self.classifier.classify(subject, description)
        logger.info(
            "step_classify_done",
            category=classification.category,
            priority=classification.priority,
        )

        # ── Step 2: Retrieve ───────────────────────────────
        context = await self.retriever.retrieve_context(subject, description)
        logger.info(
            "step_retrieve_done",
            chunks=len(context.chunks),
            sources=context.source_documents,
        )

        # ── Step 3: Generate ───────────────────────────────
        response = await self.generator.generate_response(
            subject=subject,
            description=description,
            context=context.formatted_context,
            source_documents=context.source_documents,
            customer_name=customer_name,
            conversation_history=conversation_history,
        )
        logger.info("step_generate_done", tokens=response.output_tokens)

        # ── Step 4: Evaluate ───────────────────────────────
        evaluation = await self.evaluator.evaluate(
            ticket_subject=subject,
            ticket_description=description,
            generated_response=response.response_text,
            context=context.formatted_context,
        )
        logger.info(
            "step_evaluate_done",
            score=evaluation.overall_score,
            safe=evaluation.is_safe_to_send,
        )

        result = OrchestrationResult(
            classification=classification,
            context=context,
            response=response,
            evaluation=evaluation,
        )

        logger.info(
            "orchestration_complete",
            ticket_id=ticket_id,
            overall_score=evaluation.overall_score,
        )
        return result
