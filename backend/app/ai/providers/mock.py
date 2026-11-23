"""
SupportPilot AI — Mock / Test LLM Provider
Provides deterministic, testable LLM completions and structured outputs
for automated unit/integration tests without requiring network calls or cloud API keys.
"""

import json
from typing import AsyncIterator, Type, TypeVar
from pydantic import BaseModel

from app.ai.providers.base import (
    CompletionOptions,
    CompletionResult,
    LLMProvider,
    Message,
)
from app.ai.providers.embeddings import LocalDeterministicEmbeddingProvider
from app.schemas.ai import (
    ClassificationOutput,
    CustomerSentiment,
    DocumentCitation,
    EvaluationReport,
    EvaluationVerdict,
    GenerationOutput,
    RetrievalAssessment,
    TicketCategory,
    TicketUrgency,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """
    Deterministic LLM provider for testing and offline environments.
    Inspects messages to return context-aware mocked responses.
    """

    def __init__(self, model_name: str = "mock-gemini-1.5"):
        self.model_name = model_name
        self._embedder = LocalDeterministicEmbeddingProvider()
        self.call_history: list[list[Message]] = []
        self.override_response: str | None = None
        self.override_structured: BaseModel | None = None

    async def complete(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> CompletionResult:
        self.call_history.append(messages)
        if self.override_response:
            return CompletionResult(
                content=self.override_response,
                model=self.model_name,
                input_tokens=100,
                output_tokens=50,
            )

        # Detect the type of prompt by looking at the system/user content
        all_text = " ".join([m.content for m in messages]).lower()
        user_messages = [m for m in messages if m.role == "user"]
        user_text = " ".join([m.content for m in user_messages]).lower() if user_messages else all_text

        # 1. Classification
        if "classification" in all_text or "categorize" in all_text:
            output = self._mock_classification(user_text)
            content = output.model_dump_json()

        # 2. Evaluation
        elif "evaluate" in all_text or "quality assurance" in all_text:
            output = self._mock_evaluation(user_text)
            content = output.model_dump_json()

        # 3. Generation
        elif "draft a response" in all_text or "response generator" in all_text:
            output = self._mock_generation(user_text)
            content = output.model_dump_json()

        # 4. Query expansion
        elif "alternative search queries" in all_text or "query expansion" in all_text:
            content = json.dumps(["refund policy timeline", "hardware return requirements"])

        else:
            content = (
                "SupportPilot AI Assistant: Thank you for contacting customer support. "
                "Based on our documentation, your request is being processed."
            )

        return CompletionResult(
            content=content,
            model=self.model_name,
            input_tokens=120,
            output_tokens=80,
        )

    async def complete_structured(
        self,
        messages: list[Message],
        response_model: Type[T],
        options: CompletionOptions | None = None,
    ) -> T:
        if self.override_structured and isinstance(self.override_structured, response_model):
            return self.override_structured  # type: ignore

        res = await self.complete(messages, options)
        try:
            return response_model.model_validate_json(res.content)
        except Exception:
            return await super().complete_structured(messages, response_model, options)

    async def stream(
        self,
        messages: list[Message],
        options: CompletionOptions | None = None,
    ) -> AsyncIterator[str]:
        full_res = await self.complete(messages, options)
        words = full_res.content.split()
        for word in words:
            yield word + " "

    async def embed(self, text: str) -> list[float]:
        return await self._embedder.embed_text(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._embedder.embed_batch(texts)

    # ── Internal Generators ───────────────────────────────────

    def _mock_classification(self, text: str) -> ClassificationOutput:
        # Check for angry / urgent / immediate escalation triggers
        if any(w in text for w in ["lawsuit", "sue", "lawyer", "unacceptable", "furious", "manager", "human"]):
            return ClassificationOutput(
                category=TicketCategory.GENERAL_INQUIRY,
                priority=TicketUrgency.URGENT,
                sentiment=CustomerSentiment.ANGRY,
                urgency_score=0.95,
                requires_immediate_human=True,
                confidence=0.92,
                summary="Customer demanding immediate human supervisor or expressing severe dissatisfaction.",
                reasoning="Escalation keywords detected in customer message.",
            )

        if "refund" in text or "billing" in text or "invoice" in text or "charge" in text:
            return ClassificationOutput(
                category=TicketCategory.BILLING,
                priority=TicketUrgency.MEDIUM,
                sentiment=CustomerSentiment.NEUTRAL,
                urgency_score=0.45,
                requires_immediate_human=False,
                confidence=0.95,
                summary="Customer inquiry regarding billing or refund eligibility.",
                reasoning="Identified billing and refund terms in request.",
            )

        if "error" in text or "crash" in text or "bug" in text or "api" in text or "latency" in text:
            return ClassificationOutput(
                category=TicketCategory.TECHNICAL,
                priority=TicketUrgency.HIGH,
                sentiment=CustomerSentiment.FRUSTRATED,
                urgency_score=0.75,
                requires_immediate_human=False,
                confidence=0.88,
                summary="Technical error or system defect reported.",
                reasoning="Technical bug signatures found.",
            )

        return ClassificationOutput(
            category=TicketCategory.GENERAL_INQUIRY,
            priority=TicketUrgency.LOW,
            sentiment=CustomerSentiment.POSITIVE,
            urgency_score=0.2,
            requires_immediate_human=False,
            confidence=0.85,
            summary="General customer inquiry.",
            reasoning="Standard question.",
        )

    def _mock_generation(self, text: str) -> GenerationOutput:
        # If there's knowledge context about refund policy
        if "refund" in text and "30 days" in text:
            return GenerationOutput(
                response_text=(
                    "Hello! In accordance with our official policy [Doc: Acme Refund Policy #0], "
                    "you may request a full refund within 30 days of initial purchase with proof of transaction. "
                    "Subscriptions are billed monthly and can be cancelled anytime with pro-rated credit. "
                    "Hardware items have a 14-day return window in their original packaging. "
                    "Please let us know if you need help initiating this return!"
                ),
                confidence_score=0.96,
                citations=["Acme Refund Policy #0"],
                has_missing_info=False,
                unanswered_questions=[],
                suggested_action="reply_to_customer",
            )

        # If knowledge context is absent or missing information
        if "no relevant documents" in text or "context: none" in text or "missing" in text:
            return GenerationOutput(
                response_text=(
                    "Hello! We have received your inquiry. However, our knowledge base does not contain "
                    "specific documentation regarding this question. I have routed your ticket to a human "
                    "support specialist who will verify the details and reply shortly."
                ),
                confidence_score=0.35,
                citations=[],
                has_missing_info=True,
                unanswered_questions=["Customer specific request not in KB"],
                suggested_action="escalate_to_human",
            )

        return GenerationOutput(
            response_text=(
                "Hello! Thank you for reaching out to SupportPilot support. Based on our company documentation, "
                "we are reviewing your account details. A customer support representative will follow up with you."
            ),
            confidence_score=0.8,
            citations=[],
            has_missing_info=False,
            unanswered_questions=[],
            suggested_action="reply_to_customer",
        )

    def _mock_evaluation(self, text: str) -> EvaluationReport:
        # If the generated response claims something unsupported or missing context
        if "hallucinate_test" in text or "unsupported claim" in text:
            return EvaluationReport(
                groundedness_score=0.30,
                relevance_score=0.50,
                tone_score=0.80,
                overall_score=0.45,
                hallucination_detected=True,
                unsupported_claims=["Response promised a 90% lifetime discount not found in KB."],
                verdict=EvaluationVerdict.ESCALATE,
                escalation_reason="Hallucination detected: unauthorized policy promise.",
            )

        if "has_missing_info" in text or "no relevant documents" in text:
            return EvaluationReport(
                groundedness_score=0.95,
                relevance_score=0.60,
                tone_score=0.90,
                overall_score=0.65,
                hallucination_detected=False,
                unsupported_claims=[],
                verdict=EvaluationVerdict.ESCALATE,
                escalation_reason="Insufficient knowledge base coverage to answer customer inquiry safely.",
            )

        return EvaluationReport(
            groundedness_score=0.95,
            relevance_score=0.92,
            tone_score=0.94,
            overall_score=0.94,
            hallucination_detected=False,
            unsupported_claims=[],
            verdict=EvaluationVerdict.APPROVE,
            escalation_reason=None,
        )
