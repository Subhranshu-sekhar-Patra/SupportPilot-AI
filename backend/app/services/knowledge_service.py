"""
SupportPilot AI — Knowledge Base Service
Handles document lifecycle: upload, storage, indexing in ChromaDB, re-indexing, and semantic search.
Strictly isolated by organization.
"""

import os
import shutil
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.embeddings import get_embedding_provider
from app.ai.rag.ingestion import DocumentIngestionService
from app.ai.rag.retrieval import RetrievalService
from app.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logger import get_logger
from app.models.knowledge import DocumentStatus, KnowledgeDocument
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    QueryKnowledgeRequest,
    QueryKnowledgeResponse,
    RetrievedChunkResponse,
)

logger = get_logger(__name__)


class KnowledgeService:
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.user = current_user
        self.org_id = current_user.organization_id

    async def list_documents(self) -> KnowledgeDocumentListResponse:
        """List all knowledge base documents for caller's organization."""
        query = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.organization_id == self.org_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        result = await self.db.execute(query)
        docs = result.scalars().all()

        return KnowledgeDocumentListResponse(
            items=[KnowledgeDocumentResponse.model_validate(d) for d in docs],
            total=len(docs),
        )

    async def get_document(self, document_id: str) -> KnowledgeDocumentResponse:
        """Get document details by ID."""
        doc = await self._get_doc_or_404(document_id)
        return KnowledgeDocumentResponse.model_validate(doc)

    async def upload_document(
        self,
        file: UploadFile,
        title: str | None = None,
        tags: list[str] | None = None,
        run_async: bool = False,
    ) -> KnowledgeDocumentResponse:
        """
        Validate file, store on disk, create DB record, and trigger ingestion.
        """
        filename = file.filename or "uploaded_document"
        ext = Path(filename).suffix.lower().lstrip(".")

        if ext not in settings.allowed_upload_types_list:
            raise ValidationError(
                f"Unsupported file type: .{ext}. Allowed: {settings.allowed_upload_types}"
            )

        # Ensure upload dir exists
        upload_dir = Path(settings.upload_dir) / self.org_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        target_path = upload_dir / filename

        # Save file to disk
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            file_size = target_path.stat().st_size

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if file_size > max_bytes:
            target_path.unlink(missing_ok=True)
            raise ValidationError(
                f"File size exceeds maximum allowed of {settings.max_upload_size_mb}MB"
            )

        doc_title = title.strip() if title else Path(filename).stem.replace("_", " ").title()

        doc = KnowledgeDocument(
            title=doc_title,
            file_name=filename,
            file_type=ext,
            file_size_bytes=file_size,
            storage_path=str(target_path),
            status=DocumentStatus.PENDING,
            organization_id=self.org_id,
            uploaded_by_id=self.user.id,
            tags=tags or [],
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        logger.info("knowledge_doc_uploaded", document_id=doc.id, org_id=self.org_id)

        # Process ingestion immediately unless deferred
        if not run_async:
            await self.process_ingestion(doc.id)
            await self.db.refresh(doc)

        return KnowledgeDocumentResponse.model_validate(doc)

    async def process_ingestion(self, document_id: str) -> None:
        """Extract text, chunk, embed, and index document in ChromaDB."""
        doc = await self._get_doc_or_404(document_id)
        doc.status = DocumentStatus.PROCESSING
        await self.db.commit()

        try:
            embedder = get_embedding_provider()
            ingestor = DocumentIngestionService(embedder, self.org_id)
            chunk_ids = await ingestor.ingest_file(
                file_path=doc.storage_path,
                document_id=doc.id,
                document_title=doc.title,
                tags=doc.tags,
            )

            doc.status = DocumentStatus.INDEXED
            doc.chunk_count = len(chunk_ids)
            doc.chroma_ids = chunk_ids
            doc.error_message = None
            logger.info("knowledge_doc_indexed", document_id=doc.id, chunks=len(chunk_ids))
        except Exception as e:
            logger.error("knowledge_ingestion_failed", document_id=doc.id, error=str(e))
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)

        await self.db.commit()

    async def reindex_document(self, document_id: str) -> KnowledgeDocumentResponse:
        """Re-extract, re-chunk, and re-embed an existing document."""
        doc = await self._get_doc_or_404(document_id)
        if not os.path.exists(doc.storage_path):
            raise NotFoundError(f"Original file for document {document_id} was not found on disk.")

        doc.status = DocumentStatus.PROCESSING
        await self.db.commit()

        try:
            embedder = get_embedding_provider()
            ingestor = DocumentIngestionService(embedder, self.org_id)
            chunk_ids = await ingestor.reindex_document(
                file_path=doc.storage_path,
                document_id=doc.id,
                document_title=doc.title,
                tags=doc.tags,
            )

            doc.status = DocumentStatus.INDEXED
            doc.chunk_count = len(chunk_ids)
            doc.chroma_ids = chunk_ids
            doc.error_message = None
            logger.info("knowledge_doc_reindexed", document_id=doc.id, chunks=len(chunk_ids))
        except Exception as e:
            logger.error("knowledge_reindex_failed", document_id=doc.id, error=str(e))
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)

        await self.db.commit()
        await self.db.refresh(doc)
        return KnowledgeDocumentResponse.model_validate(doc)

    async def delete_document(self, document_id: str) -> None:
        """Remove document record, disk file, and all chunks from ChromaDB."""
        doc = await self._get_doc_or_404(document_id)

        # 1. Clean vectors from ChromaDB
        try:
            embedder = get_embedding_provider()
            ingestor = DocumentIngestionService(embedder, self.org_id)
            await ingestor.delete_document(document_id)
        except Exception as e:
            logger.warning("chroma_delete_failed", document_id=document_id, error=str(e))

        # 2. Delete disk file
        if os.path.exists(doc.storage_path):
            try:
                os.remove(doc.storage_path)
            except OSError as e:
                logger.warning("file_delete_failed", path=doc.storage_path, error=str(e))

        # 3. Delete DB record
        await self.db.delete(doc)
        await self.db.commit()
        logger.info("knowledge_doc_deleted", document_id=document_id, org_id=self.org_id)

    async def query_knowledge(self, req: QueryKnowledgeRequest) -> QueryKnowledgeResponse:
        """Perform semantic search on caller's organization vector store."""
        embedder = get_embedding_provider()
        retrieval = RetrievalService(embedder, self.org_id)
        chunks = await retrieval.retrieve(
            query=req.query,
            top_k=req.top_k,
            min_similarity=req.min_similarity,
        )

        results = [
            RetrievedChunkResponse(
                chunk_id=c.chunk_id,
                content=c.content,
                document_id=c.document_id,
                document_title=c.document_title,
                chunk_index=c.chunk_index,
                similarity_score=c.similarity_score,
                source=c.source,
            )
            for c in chunks
        ]

        return QueryKnowledgeResponse(
            query=req.query,
            results=results,
            total_found=len(results),
        )

    async def _get_doc_or_404(self, document_id: str) -> KnowledgeDocument:
        result = await self.db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.organization_id == self.org_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("KnowledgeDocument")
        return doc
