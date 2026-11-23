"""
SupportPilot AI — Knowledge Base Pydantic Schemas
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from app.models.knowledge import DocumentStatus


class KnowledgeDocumentResponse(BaseModel):
    id: str
    title: str
    file_name: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus
    chunk_count: int
    tags: list[str] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentResponse]
    total: int


class QueryKnowledgeRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Search query string")
    top_k: int = Field(5, ge=1, le=20)
    min_similarity: float = Field(0.4, ge=0.0, le=1.0)


class RetrievedChunkResponse(BaseModel):
    chunk_id: str
    content: str
    document_id: str
    document_title: str
    chunk_index: int
    similarity_score: float
    source: str


class QueryKnowledgeResponse(BaseModel):
    query: str
    results: list[RetrievedChunkResponse]
    total_found: int
