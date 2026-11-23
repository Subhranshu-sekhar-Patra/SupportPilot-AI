"""
SupportPilot AI — Comprehensive AI Agent Engine Test Suite (Phase 5)

Tests:
  1. Query Classification Agent (intents, sentiments, urgency, immediate human triggers)
  2. Knowledge Retrieval Agent (semantic search, sufficiency assessment, citations)
  3. Grounded Generator Agent (inline citations, zero-hallucination constraint, missing info handling)
  4. Response Quality Evaluator Agent (groundedness scoring, hallucination detection)
  5. Human Escalation Controller (all 4 escalation trigger rules)
  6. End-to-End Orchestrator Pipeline (Happy Path AI Auto-reply vs. Missing Info Escalation)
  7. REST API Integration (POST /api/v1/tickets/{id}/process-ai)
"""

import os
import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.agents.classifier import ClassifierAgent
from app.ai.agents.escalation import HumanEscalationController
from app.ai.agents.evaluator import EvaluatorAgent
from app.ai.agents.generator import GeneratorAgent
from app.ai.agents.retriever import RetrieverAgent
from app.ai.orchestrator import AgentOrchestrator
from app.ai.providers.mock import MockLLMProvider
from app.ai.rag.ingestion import DocumentIngestionService
from app.ai.rag.retrieval import RetrievalService
from app.core.middleware import reset_rate_limiters
from app.main import app
from app.models.ticket import TicketPriority, TicketStatus
from app.schemas.ai import (
    CustomerSentiment,
    EvaluationVerdict,
    TicketCategory,
    TicketUrgency,
)


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


# ── 1. Classification Agent Tests ─────────────────────────────

@pytest.mark.anyio
async def test_classifier_standard_billing_inquiry(mock_llm):
    classifier = ClassifierAgent(mock_llm)
    res = await classifier.classify(
        subject="Monthly Invoice Question",
        description="I have a question about the invoice charge for my subscription and refund options.",
    )
    assert res.category == TicketCategory.BILLING
    assert res.priority in (TicketUrgency.MEDIUM, TicketUrgency.LOW)
    assert res.requires_immediate_human is False
    assert res.confidence >= 0.70


@pytest.mark.anyio
async def test_classifier_immediate_escalation_triggers(mock_llm):
    classifier = ClassifierAgent(mock_llm)
    res = await classifier.classify(
        subject="COMPLETELY UNACCEPTABLE - TALK TO LAWYER",
        description="Your service destroyed our production database. I am furious and my lawyer is preparing a lawsuit. Connect me with your manager immediately!",
    )
    assert res.sentiment == CustomerSentiment.ANGRY
    assert res.priority == TicketUrgency.URGENT
    assert res.requires_immediate_human is True
    assert res.urgency_score >= 0.85


# ── 2. Retrieval & Sufficiency Assessment Tests ───────────────

@pytest.mark.anyio
async def test_retriever_with_policy_chunks(mock_llm, tmp_path):
    org_id = "org_retriever_test"
    ingestor = DocumentIngestionService(org_id=org_id)
    retrieval_service = RetrievalService(org_id=org_id)

    # Ingest a sample refund policy
    sample_doc = tmp_path / "acme_refund_policy.txt"
    sample_doc.write_text(
        "Acme Corp Refund Policy: All purchases are eligible for a 100% money-back guarantee within 30 days of transaction. "
        "Hardware items require a 14-day return window in undamaged original packaging.",
        encoding="utf-8",
    )

    try:
        await ingestor.ingest_document(
            doc_id="refund_doc_01",
            file_path=str(sample_doc),
            title="Acme Refund Policy",
        )

        retriever = RetrieverAgent(mock_llm, retrieval_service)
        assessment = await retriever.retrieve_context(
            subject="Refund eligibility window",
            description="How many days do I have to request a refund for software and hardware?",
        )

        assert len(assessment.citations) >= 1
        assert assessment.has_sufficient_context is True
        assert assessment.coverage_score > 0.0
        assert "Acme Refund Policy" in assessment.formatted_context
        assert len(assessment.missing_information) == 0

    finally:
        await ingestor.delete_document("refund_doc_01")


# ── 3. Grounded Generator Agent Tests ─────────────────────────

@pytest.mark.anyio
async def test_generator_includes_citations_and_policy(mock_llm, tmp_path):
    org_id = "org_generator_test"
    ingestor = DocumentIngestionService(org_id=org_id)
    retrieval_service = RetrievalService(org_id=org_id)

    sample_doc = tmp_path / "warranty.txt"
    sample_doc.write_text(
        "Warranty Terms: Enterprise server units include 30 days full refund and 3 years on-site hardware warranty.",
        encoding="utf-8",
    )

    try:
        await ingestor.ingest_document(
            doc_id="warranty_doc_01",
            file_path=str(sample_doc),
            title="Acme Refund Policy",
        )

        retriever = RetrieverAgent(mock_llm, retrieval_service)
        assessment = await retriever.retrieve_context(
            subject="Refund question",
            description="What is the 30 days refund terms?",
        )

        generator = GeneratorAgent(mock_llm)
        response = await generator.generate_response(
            subject="Refund question",
            description="Can I get a refund in 30 days?",
            retrieval=assessment,
            customer_name="Alex Smith",
        )

        assert "[Doc:" in response.response_text or len(response.citations) > 0
        assert response.confidence_score >= 0.80
        assert response.has_missing_info is False

    finally:
        await ingestor.delete_document("warranty_doc_01")


@pytest.mark.anyio
async def test_generator_detects_missing_information(mock_llm):
    # Empty retrieval assessment (no documents in KB)
    from app.schemas.ai import RetrievalAssessment

    empty_assessment = RetrievalAssessment(
        search_queries=["quantum propulsion drive installation"],
        has_sufficient_context=False,
        coverage_score=0.0,
        missing_information=["No documentation found for quantum drive"],
        citations=[],
        formatted_context="No relevant documents found.",
    )

    generator = GeneratorAgent(mock_llm)
    response = await generator.generate_response(
        subject="Quantum Propulsion Query",
        description="How do I configure the tachyon emitter?",
        retrieval=empty_assessment,
        customer_name="Commander Spock",
    )

    # When context is missing, generator must NOT invent fake policies
    assert response.has_missing_info is True
    assert response.suggested_action == "escalate_to_human"


# ── 4. Evaluator Agent & Hallucination Defense ────────────────

@pytest.mark.anyio
async def test_evaluator_approves_grounded_response(mock_llm):
    from app.schemas.ai import GenerationOutput, RetrievalAssessment

    retrieval = RetrievalAssessment(
        has_sufficient_context=True,
        coverage_score=0.9,
        formatted_context="Acme provides 30-day refunds for all subscriptions.",
    )
    generation = GenerationOutput(
        response_text="According to our policy [Doc: Acme Policy #0], you can request a refund within 30 days.",
        confidence_score=0.95,
        citations=["Acme Policy #0"],
    )

    evaluator = EvaluatorAgent(mock_llm)
    report = await evaluator.evaluate(
        ticket_subject="Refund policy",
        ticket_description="How long do I have to refund?",
        retrieval=retrieval,
        generation=generation,
    )

    assert report.verdict == EvaluationVerdict.APPROVE
    assert report.hallucination_detected is False
    assert report.overall_score >= 0.70


@pytest.mark.anyio
async def test_evaluator_rejects_and_escalates_hallucinations(mock_llm):
    from app.schemas.ai import GenerationOutput, RetrievalAssessment

    retrieval = RetrievalAssessment(
        has_sufficient_context=True,
        coverage_score=0.9,
        formatted_context="Standard price is $50/mo. No discounts available.",
    )
    # The simulated response contains an unsupported claim / hallucinate_test
    generation = GenerationOutput(
        response_text="hallucinate_test: I can give you a 90% lifetime discount right now!",
        confidence_score=0.2,
    )

    evaluator = EvaluatorAgent(mock_llm)
    report = await evaluator.evaluate(
        ticket_subject="Discount request",
        ticket_description="Can I get 90% off?",
        retrieval=retrieval,
        generation=generation,
    )

    assert report.verdict == EvaluationVerdict.ESCALATE
    assert report.hallucination_detected is True
    assert report.overall_score < 0.70


# ── 5. Human Escalation Controller Rule Tests ─────────────────

def test_escalation_controller_all_triggers():
    controller = HumanEscalationController()
    from app.schemas.ai import (
        ClassificationOutput,
        EvaluationReport,
        GenerationOutput,
        RetrievalAssessment,
    )

    # Base benign objects
    base_class = ClassificationOutput(
        category=TicketCategory.TECHNICAL,
        priority=TicketUrgency.LOW,
        sentiment=CustomerSentiment.POSITIVE,
        requires_immediate_human=False,
    )
    base_retrieval = RetrievalAssessment(has_sufficient_context=True, coverage_score=0.85)
    base_gen = GenerationOutput(response_text="Everything is fine.", has_missing_info=False)
    base_eval = EvaluationReport(overall_score=0.92, hallucination_detected=False, verdict=EvaluationVerdict.APPROVE)

    # 1. Normal path -> should NOT escalate
    d1 = controller.decide(base_class, base_retrieval, base_gen, base_eval, conversation_turn_count=1)
    assert d1.should_escalate is False

    # 2. Trigger: Angry customer
    angry_class = ClassificationOutput(
        category=TicketCategory.BILLING,
        priority=TicketUrgency.HIGH,
        sentiment=CustomerSentiment.ANGRY,
        requires_immediate_human=True,
    )
    d2 = controller.decide(angry_class, base_retrieval, base_gen, base_eval)
    assert d2.should_escalate is True
    assert "angry" in d2.escalation_reason.lower() or "human" in d2.escalation_reason.lower()

    # 3. Trigger: Insufficient KB context
    empty_retrieval = RetrievalAssessment(has_sufficient_context=False, coverage_score=0.1)
    d3 = controller.decide(base_class, empty_retrieval, base_gen, base_eval)
    assert d3.should_escalate is True
    assert "knowledge base lacks" in d3.escalation_reason.lower()

    # 4. Trigger: Hallucination detected
    hallucinating_eval = EvaluationReport(
        overall_score=0.4,
        hallucination_detected=True,
        unsupported_claims=["Made up 90% discount."],
        verdict=EvaluationVerdict.ESCALATE,
    )
    d4 = controller.decide(base_class, base_retrieval, base_gen, hallucinating_eval)
    assert d4.should_escalate is True
    assert "hallucination" in d4.escalation_reason.lower()

    # 5. Trigger: Multi-turn loop (>= 3 turns)
    d5 = controller.decide(base_class, base_retrieval, base_gen, base_eval, conversation_turn_count=3)
    assert d5.should_escalate is True
    assert "multi-turn" in d5.escalation_reason.lower()


# ── 6. End-to-End Orchestrator Pipeline Test ──────────────────

@pytest.mark.anyio
async def test_agent_orchestrator_pipeline_flow(mock_llm, tmp_path):
    org_id = "org_orchestrator_demo"
    ingestor = DocumentIngestionService(org_id=org_id)
    retrieval_service = RetrievalService(org_id=org_id)

    # Ingest company SLA policy
    sla_file = tmp_path / "sla.txt"
    sla_file.write_text(
        "Acme SLA Policy: 30 days refund guarantee for all software tiers.",
        encoding="utf-8",
    )

    try:
        await ingestor.ingest_document("sla_doc_01", str(sla_file), "Acme Refund Policy")

        orchestrator = AgentOrchestrator(
            org_id=org_id,
            llm=mock_llm,
            retrieval_service=retrieval_service,
        )

        # Path A: Standard inquiry with KB facts -> Auto reply approved
        result_a = await orchestrator.run_pipeline(
            ticket_id="ticket_test_001",
            subject="30 days refund terms",
            description="I need information on the 30 days refund policy.",
            customer_name="Sarah Connor",
        )
        assert result_a.status == "approved"
        assert result_a.is_automated_reply is True
        assert result_a.generation is not None
        assert "Acme Refund Policy" in result_a.generation.response_text or len(result_a.generation.citations) > 0

        # Path B: Escalation when customer is furious
        result_b = await orchestrator.run_pipeline(
            ticket_id="ticket_test_002",
            subject="Furious about service lawsuit manager",
            description="I am angry and demanding to speak with a human manager immediately!",
            customer_name="Angry Customer",
        )
        assert result_b.status == "escalated"
        assert result_b.is_automated_reply is False
        assert result_b.escalation.should_escalate is True

    finally:
        await ingestor.delete_document("sla_doc_01")


# ── 7. REST API Endpoints Integration Test ────────────────────

@pytest.mark.anyio
async def test_api_process_ticket_ai_endpoint():
    """Verify POST /api/v1/tickets/{id}/process-ai runs orchestrator and updates DB."""
    reset_rate_limiters()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"ai_agent_lead_{hash('agent_test')}@ai-support.com",
                "password": "Password123!",
                "full_name": "Tony Stark",
                "organization_name": "Stark Industries AI",
            },
        )
        assert reg_res.status_code == 201, reg_res.text
        token = reg_res.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a ticket
        ticket_res = await client.post(
            "/api/v1/tickets",
            headers=headers,
            json={
                "subject": "Need invoice clarification on 30 days refund policy",
                "description": "Can you explain the 30 days refund policy for monthly billing subscriptions?",
                "customer_name": "Peter Parker",
            },
        )
        assert ticket_res.status_code == 201
        ticket_id = ticket_res.json()["id"]

        # 2. Trigger AI processing endpoint
        process_res = await client.post(
            f"/api/v1/tickets/{ticket_id}/process-ai",
            headers=headers,
        )
        assert process_res.status_code == 200
        ai_data = process_res.json()
        assert "classification" in ai_data
        assert "retrieval" in ai_data
        assert "escalation" in ai_data

        # 3. Fetch ticket to verify DB was updated
        updated_ticket = (await client.get(f"/api/v1/tickets/{ticket_id}", headers=headers)).json()
        assert updated_ticket["ai_category"] is not None
        assert updated_ticket["status"] in ("in_progress", "escalated", "open")

        # 4. Check conversation messages to verify AI message / handover note was created
        messages_res = await client.get(f"/api/v1/tickets/{ticket_id}/messages", headers=headers)
        assert messages_res.status_code == 200
        messages = messages_res.json()
        assert len(messages) >= 2  # Customer initial message + AI response or system escalation note
