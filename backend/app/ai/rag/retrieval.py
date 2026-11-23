"""
SupportPilot AI — Semantic Vector Retrieval Service
Retrieves top-k relevant knowledge base document chunks for natural language queries.
Strictly scoped to the caller's organization.
"""

from dataclasses import dataclass
from pathlib import Path
import chromadb

from app.ai.providers.embeddings import BaseEmbeddingProvider, get_embedding_provider
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A single retrieved knowledge chunk with similarity and provenance metadata."""
    chunk_id: str
    content: str
    document_id: str
    document_title: str
    file_name: str
    chunk_index: int
    similarity_score: float
    source: str


class RetrievalService:
    """
    Executes semantic vector searches against ChromaDB with strict organization isolation.
    """

    def __init__(self, embedding_provider: BaseEmbeddingProvider | None = None, org_id: str = ""):
        self.embedder = embedding_provider or get_embedding_provider()
        self.org_id = org_id
        self._client: chromadb.ClientAPI | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            persist_dir = Path(settings.chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(persist_dir))
        return self._client

    def _get_collection_name(self) -> str:
        clean_org = self.org_id.replace("-", "_").lower()
        return f"org_{clean_org}"

    async def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_similarity: float = 0.0,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Embed query, execute cosine search in ChromaDB, and return top chunks.
        """
        if not query.strip():
            return []

        collection_name = self._get_collection_name()

        # Check if collection exists
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            logger.info("collection_not_found_for_org", org_id=self.org_id, collection=collection_name)
            return []

        # Generate query embedding
        query_vector = await self.embedder.embed(query)

        # Build where clause enforcing organization isolation
        where_clause: dict = {"organization_id": self.org_id}
        if document_ids and len(document_ids) == 1:
            where_clause["document_id"] = document_ids[0]
        elif document_ids and len(document_ids) > 1:
            where_clause = {
                "$and": [
                    {"organization_id": self.org_id},
                    {"document_id": {"$in": document_ids}},
                ]
            }

        try:
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=min(top_k, max(1, collection.count())),
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("chroma_search_failed", error=str(e), org_id=self.org_id)
            return []

        retrieved: list[RetrievedChunk] = []

        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for i, chunk_id in enumerate(ids):
                doc_text = docs[i] if i < len(docs) else ""
                meta = metas[i] if i < len(metas) else {}
                dist = distances[i] if i < len(distances) else 1.0

                # Convert cosine distance to similarity score in [0.0, 1.0]
                similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))

                if similarity < min_similarity:
                    continue

                retrieved.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        content=doc_text,
                        document_id=str(meta.get("document_id", "")),
                        document_title=str(meta.get("document_title", "")),
                        file_name=str(meta.get("file_name", "")),
                        chunk_index=int(meta.get("chunk_index", 0)),
                        similarity_score=round(similarity, 4),
                        source=f"{meta.get('document_title', 'Document')} ({meta.get('file_name', '')})",
                    )
                )

        retrieved.sort(key=lambda x: x.similarity_score, reverse=True)
        logger.info(
            "retrieval_completed",
            query_preview=query[:60],
            chunks_found=len(retrieved),
            org_id=self.org_id,
        )
        return retrieved
