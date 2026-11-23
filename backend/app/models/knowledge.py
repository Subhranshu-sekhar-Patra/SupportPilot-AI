"""
SupportPilot AI — Knowledge Document Model
Stores metadata about documents ingested into the RAG vector store.
"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"       # Uploaded, not yet processed
    PROCESSING = "processing" # Being chunked and embedded
    INDEXED = "indexed"       # Successfully in ChromaDB
    FAILED = "failed"         # Ingestion failed


class KnowledgeDocument(UUIDMixin, TimestampMixin, Base):
    """
    Tracks documents uploaded to the knowledge base.
    Actual vector data lives in ChromaDB; this model stores metadata.
    """

    __tablename__ = "knowledge_documents"

    # File info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Processing
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False, index=True
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ChromaDB references
    chroma_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Metadata for filtering during retrieval
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Multi-tenancy
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ──────────────────────────────────────
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization", back_populates="knowledge_documents"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDocument id={self.id} title={self.title} status={self.status}>"
