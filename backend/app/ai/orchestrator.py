"""
SupportPilot AI — AI Agent Workflow Orchestrator
Coordinates:
Customer Query → Classification → RAG Retrieval → Response Generation → Quality Evaluation → AI Response or Human Escalation.
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.ai.agents.classifier import ClassifierAgent
from app.ai.agents.escalation import HumanEscalationController
from app.ai.agents.evaluator import EvaluatorAgent
from app.ai.agents.generator import GeneratorAgent
from app.ai.agents.retriever import RetrieverAgent
from app.ai.providers.base import LLMProvider
from app.ai.providers.gemini import get_llm_provider
from app.ai.rag.retrieval import RetrievalService
from app.core.logger import get_logger
from app.models.ticket import MessageAuthorType, Ticket, TicketMessage, TicketPriority, TicketStatus
from app.schemas.ai import (
    AgentPipelineResult,
    ClassificationOutput,
    CustomerSentiment,
    EscalationDecision,
    EvaluationReport,
    GenerationOutput,
    RetrievalAssessment,
    TicketUrgency,
)

logger = get_logger(__name__)


class AgentOrchestrator:
    """
    Coordinates the 5-agent AI workflow for customer support tickets.
    Ensures multi-tenant isolation, strict fact grounding, and automated quality assurance.
    """

    def __init__(
        self,
        org_id: str,
        llm: LLMProvider | None = None,
        retrieval_service: RetrievalService | None = None,
    ):
        self.org_id = org_id
        self.llm = llm or get_llm_provider()
        self.retrieval_service = retrieval_service or RetrievalService(org_id=org_id)

        self.classifier = ClassifierAgent(self.llm)
        self.retriever = RetrieverAgent(self.llm, self.retrieval_service)
        self.generator = GeneratorAgent(self.llm)
        self.evaluator = EvaluatorAgent(self.llm)
        self.escalation_controller = HumanEscalationController()

    async def run_pipeline(
        self,
        ticket_id: str,
        subject: str,
        description: str,
        customer_name: str | None = None,
        conversation_history: list[dict] | None = None,
        auto_reply_threshold: float = 0.70,
    ) -> AgentPipelineResult:
        """
        Execute the end-to-end AI agent workflow.
        """
        logger.info("ai_workflow_started", ticket_id=ticket_id, org_id=self.org_id)

        # ── Step 1: Query Classification ──────────────────────────
        classification: ClassificationOutput = await self.classifier.classify(
            subject=subject,
            description=description,
            conversation_history=conversation_history,
        )

        # ── Step 2: Knowledge Retrieval (RAG) ────────────────────
        retrieval: RetrievalAssessment = await self.retriever.retrieve_context(
            subject=subject,
            description=description,
            top_k=4,
        )

        # Count previous AI messages to prevent infinite loops
        turn_count = 1
        if conversation_history:
            ai_turns = sum(1 for m in conversation_history if m.get("author_type") == "ai")
            turn_count = ai_turns + 1

        # ── Step 3: Response Generation ──────────────────────────
        generation: GenerationOutput | None = None
        evaluation: EvaluationReport | None = None

        # Check for immediate escalation triggers (e.g. angry customer, explicit human request)
        if classification.requires_immediate_human or classification.sentiment == CustomerSentiment.ANGRY:
            logger.info("skipping_generation_due_to_immediate_escalation", ticket_id=ticket_id)
            escalation = self.escalation_controller.decide(
                classification=classification,
                retrieval=retrieval,
                generation=None,
                evaluation=None,
                conversation_turn_count=turn_count,
            )
            return AgentPipelineResult(
                ticket_id=ticket_id,
                organization_id=self.org_id,
                status="escalated",
                classification=classification,
                retrieval=retrieval,
                generation=None,
                evaluation=None,
                escalation=escalation,
                is_automated_reply=False,
                model_used=getattr(self.llm, "model_name", "gemini-1.5-pro"),
            )

        # Generate response grounded in retrieved context
        generation = await self.generator.generate_response(
            subject=subject,
            description=description,
            retrieval=retrieval,
            customer_name=customer_name,
            conversation_history=conversation_history,
        )

        # ── Step 4: Quality & Groundedness Evaluation ────────────
        evaluation = await self.evaluator.evaluate(
            ticket_subject=subject,
            ticket_description=description,
            retrieval=retrieval,
            generation=generation,
        )

        # ── Step 5: Escalation Decision ──────────────────────────
        escalation = self.escalation_controller.decide(
            classification=classification,
            retrieval=retrieval,
            generation=generation,
            evaluation=evaluation,
            conversation_turn_count=turn_count,
        )

        # Determine if reply can be autonomously sent
        can_auto_reply = (
            not escalation.should_escalate
            and evaluation.overall_score >= auto_reply_threshold
            and not evaluation.hallucination_detected
            and not generation.has_missing_info
        )

        pipeline_status = "approved" if can_auto_reply else "escalated"

        logger.info(
            "ai_workflow_completed",
            ticket_id=ticket_id,
            status=pipeline_status,
            is_automated_reply=can_auto_reply,
            score=evaluation.overall_score,
        )

        return AgentPipelineResult(
            ticket_id=ticket_id,
            organization_id=self.org_id,
            status=pipeline_status,
            classification=classification,
            retrieval=retrieval,
            generation=generation,
            evaluation=evaluation,
            escalation=escalation,
            is_automated_reply=can_auto_reply,
            model_used=getattr(self.llm, "model_name", "gemini-1.5-pro"),
        )

    async def process_and_persist_ticket(
        self,
        db: AsyncSession,
        ticket: Ticket,
        auto_reply: bool = True,
    ) -> AgentPipelineResult:
        """
        Execute the AI workflow and persist all state changes, metadata,
        citations, and messages directly into the PostgreSQL database.
        """
        # Fetch conversation history for context
        history = [
            {
                "author_type": m.author_type.value,
                "content": m.content,
                "created_at": str(m.created_at),
            }
            for m in ticket.messages
        ]

        result = await self.run_pipeline(
            ticket_id=ticket.id,
            subject=ticket.subject,
            description=ticket.description,
            customer_name=ticket.customer_name,
            conversation_history=history,
        )

        # Update ticket enrichment attributes
        ticket.ai_category = result.classification.category.value
        ticket.ai_confidence_score = result.classification.confidence

        if result.evaluation:
            ticket.ai_quality_score = result.evaluation.overall_score
        if result.generation:
            ticket.ai_suggested_response = result.generation.response_text

        ticket.ai_metadata = {
            "classification": result.classification.model_dump(),
            "retrieval": {
                "chunks_found": len(result.retrieval.citations),
                "has_sufficient_context": result.retrieval.has_sufficient_context,
                "coverage_score": result.retrieval.coverage_score,
                "missing_information": result.retrieval.missing_information,
                "citations": [c.model_dump() for c in result.retrieval.citations],
            },
            "evaluation": result.evaluation.model_dump() if result.evaluation else None,
            "escalation": result.escalation.model_dump(),
            "model_used": result.model_used,
        }

        # Apply state transitions and message persistence
        if result.escalation.should_escalate or not result.is_automated_reply:
            ticket.status = TicketStatus.ESCALATED
            if result.escalation.urgency_level == "urgent":
                ticket.priority = TicketPriority.URGENT
            elif result.escalation.urgency_level == "high":
                ticket.priority = TicketPriority.HIGH

            # Add internal handover note for human staff
            handover_msg = TicketMessage(
                ticket_id=ticket.id,
                author_type=MessageAuthorType.SYSTEM,
                author_id=None,
                content=result.escalation.internal_handover_note,
                is_internal=True,
                message_metadata={
                    "escalation_reason": result.escalation.escalation_reason,
                    "assigned_department": result.escalation.assigned_department,
                    "ai_evaluation": result.evaluation.model_dump() if result.evaluation else None,
                },
            )
            db.add(handover_msg)

        elif auto_reply and result.is_automated_reply and result.generation:
            # Ticket is answered by AI
            ticket.status = TicketStatus.IN_PROGRESS

            ai_reply_msg = TicketMessage(
                ticket_id=ticket.id,
                author_type=MessageAuthorType.AI,
                author_id=None,
                content=result.generation.response_text,
                is_internal=False,
                message_metadata={
                    "citations": result.generation.citations,
                    "confidence": result.generation.confidence_score,
                    "quality_score": result.evaluation.overall_score if result.evaluation else None,
                    "model_used": result.model_used,
                },
            )
            db.add(ai_reply_msg)

        await db.commit()
        await db.refresh(ticket)
        return result
