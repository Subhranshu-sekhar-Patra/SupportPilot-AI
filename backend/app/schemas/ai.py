"""
SupportPilot AI — Pydantic Schemas for AI Agent Engine
Enforces strict JSON schema validation for all agent outputs.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# ── Classification Enums ──────────────────────────────────────

class TicketCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL_INQUIRY = "general_inquiry"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class CustomerSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"


class TicketUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ── Agent 1: Classifier Output Schema ─────────────────────────

class ClassificationOutput(BaseModel):
    category: TicketCategory = Field(
        default=TicketCategory.GENERAL_INQUIRY,
        description="Categorization of customer request",
    )
    priority: TicketUrgency = Field(
        default=TicketUrgency.MEDIUM,
        description="Assigned ticket urgency/priority",
    )
    sentiment: CustomerSentiment = Field(
        default=CustomerSentiment.NEUTRAL,
        description="Detected customer sentiment",
    )
    urgency_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Numerical score from 0.0 (trivial) to 1.0 (emergency)",
    )
    requires_immediate_human: bool = Field(
        default=False,
        description="True if customer is angry, demanding human, or raising legal/security threats",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score for this classification",
    )
    summary: str = Field(
        default="",
        description="1-sentence summary of customer problem",
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the classification decision",
    )


# ── Agent 2: Knowledge Retrieval Assessment Schema ───────────

class DocumentCitation(BaseModel):
    document_id: str
    document_title: str
    chunk_index: int
    relevance_score: float = Field(ge=0.0, le=1.0)
    snippet: str


class RetrievalAssessment(BaseModel):
    search_queries: list[str] = Field(
        default_factory=list,
        description="Generated expanded search queries used for vector lookup",
    )
    has_sufficient_context: bool = Field(
        default=False,
        description="True if retrieved knowledge base chunks contain answers to the query",
    )
    coverage_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimated coverage ratio of customer inquiry by retrieved facts",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Aspects of customer inquiry not covered by knowledge base",
    )
    citations: list[DocumentCitation] = Field(
        default_factory=list,
        description="Retrieved source document citations",
    )
    formatted_context: str = Field(
        default="",
        description="Aggregated text context supplied to generation prompt",
    )


# ── Agent 3: Response Generation Schema ──────────────────────

class GenerationOutput(BaseModel):
    response_text: str = Field(
        ...,
        description="Helpful, empathetic response with inline citations [Doc: <title> #<chunk>]",
    )
    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in generated response accuracy",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="List of cited document references",
    )
    has_missing_info: bool = Field(
        default=False,
        description="True if response acknowledges missing company policy or info",
    )
    unanswered_questions: list[str] = Field(
        default_factory=list,
        description="Questions from customer that could not be verified by context",
    )
    suggested_action: str = Field(
        default="reply_to_customer",
        description="Next recommended step",
    )


# ── Agent 4: Response Evaluation Schema ───────────────────────

class EvaluationVerdict(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"


class EvaluationReport(BaseModel):
    groundedness_score: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Faithfulness score: is every factual statement supported by context?",
    )
    relevance_score: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Relevance score: does the response directly answer the customer?",
    )
    tone_score: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Tone score: empathy, clarity, and professionalism",
    )
    overall_score: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Harmonic/weighted composite quality score",
    )
    hallucination_detected: bool = Field(
        default=False,
        description="True if response contains unsupported claims or fabricated policies",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="List of statements not grounded in source context",
    )
    verdict: EvaluationVerdict = Field(
        default=EvaluationVerdict.APPROVE,
        description="Final automated QA verdict",
    )
    escalation_reason: str | None = Field(
        default=None,
        description="Reason for escalation if verdict is ESCALATE",
    )


# ── Agent 5: Human Escalation Controller Schema ───────────────

class EscalationDecision(BaseModel):
    should_escalate: bool = Field(
        default=False,
        description="True if ticket should be handed over to a human agent",
    )
    escalation_reason: str = Field(
        default="",
        description="Primary rationale for escalation",
    )
    urgency_level: str = Field(
        default="medium",
        description="Recommended ticket priority after escalation",
    )
    assigned_department: str = Field(
        default="tier_1_support",
        description="Recommended support team",
    )
    internal_handover_note: str = Field(
        default="",
        description="Concise briefing note for the human agent explaining context and next steps",
    )


# ── Pipeline Orchestration Result Schema ──────────────────────

class AgentPipelineResult(BaseModel):
    ticket_id: str
    organization_id: str
    status: str
    classification: ClassificationOutput
    retrieval: RetrievalAssessment
    generation: GenerationOutput | None = None
    evaluation: EvaluationReport | None = None
    escalation: EscalationDecision
    is_automated_reply: bool = Field(
        default=False,
        description="True if response was verified and posted to customer thread",
    )
    model_used: str = "gemini-1.5-pro"
