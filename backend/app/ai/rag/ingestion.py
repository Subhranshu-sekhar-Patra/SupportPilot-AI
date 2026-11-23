"""
SupportPilot AI — Document Ingestion Pipeline
Handles text extraction, preprocessing, chunking, embedding, and storage in ChromaDB.
Strictly isolated by organization.
"""

from pathlib import Path
from typing import Sequence

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.providers.embeddings import BaseEmbeddingProvider, get_embedding_provider
from app.ai.rag.text_extractor import DocumentTextExtractor
from app.config import settings
from app.core.exceptions import ValidationError
from app.core.logger import get_logger

logger = get_logger(__name__)


def get_chroma_client() -> chromadb.ClientAPI:
    """Return persistent local ChromaDB client storing data in chroma_persist_dir."""
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


class DocumentIngestionService:
    """
    Ingests documents into ChromaDB vector store with organization-level isolation.
    """

    def __init__(self, embedding_provider: BaseEmbeddingProvider | None = None, org_id: str = ""):
        self.embedder = embedding_provider or get_embedding_provider()
        self.org_id = org_id
        self._client: chromadb.ClientAPI | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = get_chroma_client()
        return self._client

    def _get_collection_name(self) -> str:
        """Create a sanitized, isolated collection name for the organization."""
        clean_org = self.org_id.replace("-", "_").lower()
        return f"org_{clean_org}"

    def get_or_create_collection(self):
        """Get or create the organization's dedicated vector collection."""
        collection_name = self._get_collection_name()
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"organization_id": self.org_id, "hnsw:space": "cosine"},
        )

    async def ingest_file(
        self,
        file_path: str,
        document_id: str,
        document_title: str,
        tags: list[str] | None = None,
    ) -> list[str]:
        """
        Extract text, chunk with LangChain, embed vectors, and store in ChromaDB.
        """
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(f"File not found on disk: {file_path}")

        logger.info(
            "ingestion_started",
            document_id=document_id,
            filename=path.name,
            org_id=self.org_id,
        )

        # 1. Extract and clean text using PyMuPDF / docx / text decoder
        full_text = DocumentTextExtractor.extract(str(path))
        logger.info("text_extracted", char_count=len(full_text), document_id=document_id)

        # 2. Chunk text with LangChain RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )
        raw_chunks = splitter.split_text(full_text)
        if not raw_chunks:
            raise ValidationError("Document produced 0 text chunks during splitting.")

        logger.info("text_chunked", total_chunks=len(raw_chunks), document_id=document_id)

        # 3. Generate embeddings
        embeddings = await self.embedder.embed_batch(raw_chunks)

        # 4. Prepare ChromaDB payload with comprehensive source metadata
        chunk_ids: list[str] = []
        metadatas: list[dict] = []
        documents: list[str] = []

        tags_str = ",".join(tags) if tags else ""

        for idx, (chunk_text, embedding) in enumerate(zip(raw_chunks, embeddings)):
            cid = f"{document_id}_c{idx:03d}"
            chunk_ids.append(cid)
            documents.append(chunk_text)
            metadatas.append(
                {
                    "document_id": document_id,
                    "document_title": document_title,
                    "file_name": path.name,
                    "organization_id": self.org_id,
                    "chunk_index": idx,
                    "total_chunks": len(raw_chunks),
                    "tags": tags_str,
                }
            )

        # 5. Store in ChromaDB
        collection = self.get_or_create_collection()
        collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "ingestion_completed",
            document_id=document_id,
            chunks_stored=len(chunk_ids),
            collection=self._get_collection_name(),
        )
        return chunk_ids

    async def delete_document(self, document_id: str) -> None:
        """Remove all chunks associated with a document from ChromaDB."""
        try:
            collection = self.get_or_create_collection()
            collection.delete(where={"document_id": document_id})
            logger.info("document_deleted_from_chroma", document_id=document_id, org_id=self.org_id)
        except Exception as e:
            logger.warning("chroma_delete_document_error", document_id=document_id, error=str(e))

    async def reindex_document(
        self,
        file_path: str,
        document_id: str,
        document_title: str,
        tags: list[str] | None = None,
    ) -> list[str]:
        """Delete old chunks and re-ingest document."""
        await self.delete_document(document_id)
        return await self.ingest_file(
            file_path=file_path,
            document_id=document_id,
            document_title=document_title,
            tags=tags,
        )
