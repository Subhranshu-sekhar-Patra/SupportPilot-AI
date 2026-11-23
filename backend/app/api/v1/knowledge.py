"""
SupportPilot AI — Knowledge Base API Endpoints (v1)
Multi-tenant document ingestion, semantic search, and lifecycle management.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import CurrentUser, require_role
from app.models.user import UserRole
from app.schemas.knowledge import (
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    QueryKnowledgeRequest,
    QueryKnowledgeResponse,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base & RAG"])


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
    summary="Upload and index document (PDF, DOCX, TXT, MD)",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    tags: str | None = Form(None),
    is_async: bool = Form(False),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN, UserRole.AGENT)),
) -> KnowledgeDocumentResponse:
    """
    Upload a document (PDF, DOCX, TXT, MD) and chunk/embed into ChromaDB.
    Large documents can set is_async=True for non-blocking background ingestion.
    """
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    service = KnowledgeService(db, current_user)

    doc_resp = await service.upload_document(
        file=file,
        title=title,
        tags=parsed_tags,
        run_async=is_async,
    )

    if is_async:
        background_tasks.add_task(service.process_ingestion, doc_resp.id)

    return doc_resp


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentResponse:
    """Get single document details by ID."""
    return await KnowledgeService(db, current_user).get_document(document_id)


@router.post("/{document_id}/reindex", response_model=KnowledgeDocumentResponse)
async def reindex_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> KnowledgeDocumentResponse:
    """Re-extract, re-chunk, and re-embed an existing document."""
    return await KnowledgeService(db, current_user).reindex_document(document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> None:
    """Delete document and purge its chunks from ChromaDB."""
    await KnowledgeService(db, current_user).delete_document(document_id)


@router.post("/query", response_model=QueryKnowledgeResponse)
async def query_knowledge(
    req: QueryKnowledgeRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> QueryKnowledgeResponse:
    """Search knowledge base with natural language semantic vector retrieval."""
    return await KnowledgeService(db, current_user).query_knowledge(req)
