"""
SupportPilot AI — Human Escalation Controller
Evaluates signals across classification, retrieval, generation, and quality evaluation
to determine whether a ticket requires human agent intervention.
"""

from app.core.logger import get_logger
from app.schemas.ai import (
    ClassificationOutput,
    CustomerSentiment,
    EscalationDecision,
    EvaluationReport,
    EvaluationVerdict,
    GenerationOutput,
    RetrievalAssessment,
    TicketUrgency,
)

logger = get_logger(__name__)


class HumanEscalationController:
    """
    Decides whether a ticket should be automatically answered or escalated to human staff.
    """

    def decide(
        self,
        classification: ClassificationOutput,
        retrieval: RetrievalAssessment,
        generation: GenerationOutput | None,
        evaluation: EvaluationReport | None,
        conversation_turn_count: int = 1,
    ) -> EscalationDecision:
        """
        Evaluate all pipeline signals against escalation rules.
        """
        reasons: list[str] = []

        # ── Rule 1: Immediate Classifier Signals ─────────────────
        if classification.requires_immediate_human:
            reasons.append("Customer requested human agent, supervisor, or expressed severe dissatisfaction/threat.")

        if classification.sentiment == CustomerSentiment.ANGRY:
            reasons.append("Customer sentiment is angry; human empathy required.")

        if classification.priority == TicketUrgency.URGENT and classification.urgency_score >= 0.85:
            reasons.append("Urgent priority ticket with critical impact.")

        # ── Rule 2: Knowledge Base Insufficiency ─────────────────
        if not retrieval.has_sufficient_context or retrieval.coverage_score < 0.40:
            reasons.append("Knowledge base lacks authoritative documentation to address this request.")

        # ── Rule 3: Evaluation & Hallucination Defense ───────────
        if evaluation:
            if evaluation.hallucination_detected:
                reasons.append(
                    f"Hallucination detected in draft response: {', '.join(evaluation.unsupported_claims)}"
                )
            if evaluation.verdict == EvaluationVerdict.ESCALATE:
                reasons.append(evaluation.escalation_reason or "Response quality score below safety threshold.")
            elif evaluation.overall_score < 0.70:
                reasons.append(f"Response quality score ({evaluation.overall_score:.2f}) below 0.70 threshold.")

        # ── Rule 4: Multi-Turn Conversation Loop Detection ───────
        if conversation_turn_count >= 3:
            reasons.append(
                f"Multi-turn conversation threshold reached ({conversation_turn_count} turns); escalating to avoid loop."
            )

        # ── Determine Decision ───────────────────────────────────
        should_escalate = len(reasons) > 0
        primary_reason = reasons[0] if should_escalate else "AI response meets all quality and grounding standards."

        # Assign suggested department
        cat = classification.category.value
        if cat in ("billing", "account"):
            dept = "billing_support"
        elif cat in ("technical", "bug_report", "security"):
            dept = "technical_support_tier2"
        elif cat == "compliance":
            dept = "legal_compliance"
        else:
            dept = "tier_1_support"

        # Determine priority
        if classification.priority == TicketUrgency.URGENT or classification.sentiment == CustomerSentiment.ANGRY:
            urgency = "urgent"
        elif classification.priority == TicketUrgency.HIGH:
            urgency = "high"
        else:
            urgency = "medium"

        # Generate internal briefing handover note
        handover_note = (
            f"📋 **SupportPilot AI Escalation Handover**\n"
            f"- **Escalation Reason:** {primary_reason}\n"
            f"- **Customer Sentiment:** {classification.sentiment.value.title()} (Urgency: {classification.urgency_score:.2f})\n"
            f"- **Category:** {classification.category.value.title()} → Routed to: `{dept}`\n"
            f"- **KB Context Coverage:** {retrieval.coverage_score * 100:.0f}%\n"
        )
        if retrieval.missing_information:
            handover_note += f"- **Missing Info in KB:** {'; '.join(retrieval.missing_information)}\n"
        if evaluation and evaluation.hallucination_detected:
            handover_note += f"- ⚠️ **Safety Flag:** Draft response contained unsupported claims: {evaluation.unsupported_claims}\n"

        handover_note += f"\n*Action Required: A human support specialist must review and respond directly to the customer.*"

        decision = EscalationDecision(
            should_escalate=should_escalate,
            escalation_reason=primary_reason,
            urgency_level=urgency,
            assigned_department=dept,
            internal_handover_note=handover_note,
        )

        logger.info(
            "escalation_decision_made",
            should_escalate=decision.should_escalate,
            reason=decision.escalation_reason,
            dept=decision.assigned_department,
        )
        return decision
