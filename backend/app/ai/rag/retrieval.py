"""
SupportPilot AI — RAG Retrieval Service
Finds the most relevant knowledge base chunks for a given query.
"""

from dataclasses import dataclass
from app.core.logger import get_logger
from app.ai.providers.base import LLMProvider
from app.config import settings

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A single retrieved knowledge chunk with similarity metadata."""
    chunk_id: str
    content: str
    document_id: str
    document_title: str
    chunk_index: int
    similarity_score: float
    source: str


class RetrievalService:
    def __init__(self, llm_provider: LLMProvider, org_id: str):
        self.llm = llm_provider
        self.org_id = org_id
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.AsyncHttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
        return self._client

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
        document_ids: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        query_embedding = await self.llm.embed(query)

        where: dict = {"org_id": self.org_id}
        if document_ids:
            where["document_id"] = {"$in": document_ids}
        if tags:
            where["tags"] = {"$in": tags}

        try:
            collection = await self.client.get_or_create_collection(
                name=self._collection_name()
            )

            results = await collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where if len(where) > 1 else None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("chroma_query_failed", error=str(e), org_id=self.org_id)
            return []

        chunks: list[RetrievedChunk] = []
        if results["ids"] and results["ids"][0]:
            for idx, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][idx]
                similarity = 1.0 - distance
                if similarity < min_similarity:
                    continue

                metadata = results["metadatas"][0][idx]
                chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        content=results["documents"][0][idx],
                        document_id=metadata.get("document_id", ""),
                        document_title=metadata.get("document_title", ""),
                        chunk_index=metadata.get("chunk_index", 0),
                        similarity_score=round(similarity, 4),
                        source=metadata.get("source", ""),
                    )
                )

        chunks.sort(key=lambda c: c.similarity_score, reverse=True)
        logger.info(
            "retrieval_complete",
            query_preview=query[:80],
            chunks_found=len(chunks),
            org_id=self.org_id,
        )
        return chunks

    def _collection_name(self) -> str:
        return f"{settings.chroma_collection_name}_{self.org_id}"
