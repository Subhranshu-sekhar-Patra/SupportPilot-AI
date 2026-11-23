"""
SupportPilot AI — Context Retriever Agent
Wraps the RAG retrieval service with query expansion.
"""

from dataclasses import dataclass

from app.core.logger import get_logger
from app.ai.providers.base import LLMProvider, Message, CompletionOptions
from app.ai.rag.retrieval import RetrievalService, RetrievedChunk

logger = get_logger(__name__)

_QUERY_EXPANSION_PROMPT = """Given a customer support ticket, generate 2-3 alternative 
search queries that would help retrieve relevant knowledge base articles.
Return ONLY the queries as a JSON array of strings. Example: ["query1", "query2"]"""


@dataclass
class RetrievalContext:
    chunks: list[RetrievedChunk]
    formatted_context: str
    source_documents: list[str]


class RetrieverAgent:
    """
    Retrieves relevant knowledge base context for a ticket.
    Uses query expansion to improve recall.
    """

    def __init__(self, llm: LLMProvider, retrieval_service: RetrievalService):
        self.llm = llm
        self.retrieval = retrieval_service

    async def retrieve_context(
        self,
        subject: str,
        description: str,
        top_k: int = 5,
    ) -> RetrievalContext:
        """
        Retrieve the most relevant knowledge base chunks for a ticket.

        Strategy:
          1. Retrieve using the original query
          2. Expand query and retrieve with alternatives
          3. Merge and deduplicate results, keeping highest similarity
        """
        original_query = f"{subject}\n{description}"

        # 1. Direct retrieval
        all_chunks: dict[str, RetrievedChunk] = {}
        direct_chunks = await self.retrieval.retrieve(original_query, top_k=top_k)
        for chunk in direct_chunks:
            all_chunks[chunk.chunk_id] = chunk

        # 2. Query expansion for better recall
        expanded_queries = await self._expand_query(subject, description)
        for query in expanded_queries[:2]:  # limit to avoid excessive API calls
            expanded_chunks = await self.retrieval.retrieve(query, top_k=3)
            for chunk in expanded_chunks:
                # Keep highest similarity score if duplicate
                if chunk.chunk_id not in all_chunks or \
                   chunk.similarity_score > all_chunks[chunk.chunk_id].similarity_score:
                    all_chunks[chunk.chunk_id] = chunk

        # 3. Sort and limit
        sorted_chunks = sorted(
            all_chunks.values(),
            key=lambda c: c.similarity_score,
            reverse=True,
        )[:top_k]

        # 4. Format context for injection into prompts
        formatted = self._format_context(sorted_chunks)
        sources = list({c.document_title for c in sorted_chunks})

        logger.info(
            "context_retrieved",
            chunks_count=len(sorted_chunks),
            sources=sources,
        )
        return RetrievalContext(
            chunks=sorted_chunks,
            formatted_context=formatted,
            source_documents=sources,
        )

    async def _expand_query(self, subject: str, description: str) -> list[str]:
        """Generate alternative queries to improve retrieval recall."""
        try:
            result = await self.llm.complete(
                messages=[
                    Message(role="system", content=_QUERY_EXPANSION_PROMPT),
                    Message(role="user", content=f"Subject: {subject}\nDescription: {description[:300]}"),
                ],
                options=CompletionOptions(temperature=0.5, max_tokens=256),
            )
            import json
            queries = json.loads(result.content.strip())
            if isinstance(queries, list):
                return [str(q) for q in queries[:3]]
        except Exception as e:
            logger.warning("query_expansion_failed", error=str(e))
        return []

    @staticmethod
    def _format_context(chunks: list[RetrievedChunk]) -> str:
        """Format retrieved chunks into a readable context block."""
        if not chunks:
            return "No relevant knowledge base articles found."
        lines = ["=== Relevant Knowledge Base Articles ===\n"]
        for i, chunk in enumerate(chunks, 1):
            lines.append(
                f"[{i}] Source: {chunk.document_title} (similarity: {chunk.similarity_score:.2f})\n"
                f"{chunk.content}\n"
            )
        return "\n".join(lines)
