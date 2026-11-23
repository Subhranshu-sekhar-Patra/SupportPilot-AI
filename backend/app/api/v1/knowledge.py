"""
SupportPilot AI — Knowledge Base API Endpoints (v1)
"""

from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import CurrentUser
from app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeDocumentListResponse,
    QueryKnowledgeRequest,
    QueryKnowledgeResponse,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.get("", response_model=KnowledgeDocumentListResponse)
async def list_documents(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentListResponse:
    """List all knowledge base documents for the organization."""
    return await KnowledgeService(db, current_user).list_documents()


@router.post(
    "/upload",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    tags: str | None = Form(None),
    current_user: CurrentUser = None, # injected
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentResponse:
    """
    Upload a document (PDF, TXT, MD, DOCX) and automatically index in ChromaDB.
    """
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    return await KnowledgeService(db, current_user).upload_document(
        file=file,
        title=title,
        tags=parsed_tags,
    )


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentResponse:
    """Get single document details by ID."""
    return await KnowledgeService(db, current_user).get_document(document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete document and remove all related chunks from ChromaDB."""
    await KnowledgeService(db, current_user).delete_document(document_id)


@router.post("/query", response_model=QueryKnowledgeResponse)
async def query_knowledge(
    req: QueryKnowledgeRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> QueryKnowledgeResponse:
    """Search knowledge base with natural language semantic retrieval."""
    return await KnowledgeService(db, current_user).query_knowledge(req)
