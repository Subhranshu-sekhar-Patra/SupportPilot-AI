"""
SupportPilot AI — Knowledge Retrieval Agent
Formulates targeted search queries, queries ChromaDB, and assesses context sufficiency.
"""

from app.ai.providers.base import CompletionOptions, LLMProvider, Message
from app.ai.rag.retrieval import RetrievalService, RetrievedChunk
from app.core.logger import get_logger
from app.schemas.ai import DocumentCitation, RetrievalAssessment

logger = get_logger(__name__)

_QUERY_EXPANSION_SYSTEM_PROMPT = """You are a search query formulation agent for an enterprise customer support knowledge base.
Given a customer support inquiry, generate 2-3 precise, targeted keyword search queries that would locate relevant policy, troubleshooting, or FAQ documentation.
Return ONLY a valid JSON list of strings, for example: ["refund timeline policy", "cancellation subscription terms"]
"""


class RetrieverAgent:
    """
    Retrieves and assesses knowledge base context for customer tickets.
    """

    def __init__(self, llm: LLMProvider, retrieval_service: RetrievalService):
        self.llm = llm
        self.retrieval = retrieval_service

    async def retrieve_context(
        self,
        subject: str,
        description: str,
        top_k: int = 4,
    ) -> RetrievalAssessment:
        """
        Execute vector semantic retrieval with query expansion and sufficiency scoring.
        """
        combined_query = f"{subject} {description}".strip()

        # 1. Expand search queries
        expanded_queries = await self._generate_search_queries(subject, description)
        all_queries = [combined_query] + expanded_queries

        # 2. Retrieve chunks from tenant collection
        seen_chunks: dict[str, RetrievedChunk] = {}
        for query in all_queries[:3]:
            chunks = await self.retrieval.retrieve(query, top_k=top_k)
            for chunk in chunks:
                if chunk.chunk_id not in seen_chunks or chunk.similarity_score > seen_chunks[chunk.chunk_id].similarity_score:
                    seen_chunks[chunk.chunk_id] = chunk

        sorted_chunks = sorted(
            seen_chunks.values(),
            key=lambda c: c.similarity_score,
            reverse=True,
        )[:top_k]

        # 3. Build citations and formatted context
        citations: list[DocumentCitation] = []
        context_parts: list[str] = []

        for c in sorted_chunks:
            citations.append(
                DocumentCitation(
                    document_id=c.document_id,
                    document_title=c.document_title,
                    chunk_index=c.chunk_index,
                    relevance_score=round(c.similarity_score, 3),
                    snippet=c.content[:200],
                )
            )
            context_parts.append(
                f"[Doc: {c.document_title} #{c.chunk_index} | Relevance: {c.similarity_score:.2f}]\n{c.content}"
            )

        formatted_context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."

        # 4. Assess sufficiency
        # Chunks with similarity >= 0.55 are considered relevant
        high_rel_chunks = [c for c in sorted_chunks if c.similarity_score >= 0.55]
        has_sufficient = len(high_rel_chunks) >= 1
        coverage = min(1.0, len(high_rel_chunks) * 0.45) if has_sufficient else 0.1

        missing_info = []
        if not has_sufficient:
            missing_info.append("No authoritative knowledge base document found matching customer request.")

        assessment = RetrievalAssessment(
            search_queries=all_queries,
            has_sufficient_context=has_sufficient,
            coverage_score=round(coverage, 2),
            missing_information=missing_info,
            citations=citations,
            formatted_context=formatted_context,
        )

        logger.info(
            "context_retrieved_and_assessed",
            chunks_found=len(sorted_chunks),
            sufficient=has_sufficient,
            coverage=assessment.coverage_score,
        )
        return assessment

    async def _generate_search_queries(self, subject: str, description: str) -> list[str]:
        """Generate targeted semantic search queries."""
        try:
            result = await self.llm.complete(
                messages=[
                    Message(role="system", content=_QUERY_EXPANSION_SYSTEM_PROMPT),
                    Message(role="user", content=f"Subject: {subject}\nDescription: {description[:250]}"),
                ],
                options=CompletionOptions(temperature=0.2, max_tokens=150),
            )
            import json
            raw = result.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            queries = json.loads(raw)
            if isinstance(queries, list):
                return [str(q) for q in queries if isinstance(q, str)]
        except Exception:
            pass
        return [subject]
