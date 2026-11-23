"""
SupportPilot AI — Document Ingestion Pipeline
Handles chunking, embedding, and storage in ChromaDB.
"""

from pathlib import Path
from app.core.logger import get_logger
from app.ai.providers.base import LLMProvider
from app.config import settings

logger = get_logger(__name__)


def _get_document_loader(extension: str, file_path: str):
    """Lazily load specific loader to ensure instant app startup."""
    if extension == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        return PyPDFLoader(file_path)
    elif extension == ".txt":
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path)
    elif extension == ".md":
        from langchain_community.document_loaders import UnstructuredMarkdownLoader
        return UnstructuredMarkdownLoader(file_path)
    elif extension == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader
        return Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")


def _get_splitter():
    """Lazily initialize text splitter."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _get_chroma_client():
    """Return an async ChromaDB client."""
    import chromadb
    return chromadb.AsyncHttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
    )


class DocumentIngestionService:
    def __init__(self, llm_provider: LLMProvider, org_id: str):
        self.llm = llm_provider
        self.org_id = org_id
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = _get_chroma_client()
        return self._client

    async def ingest_file(
        self,
        file_path: str,
        document_id: str,
        document_title: str,
        tags: list[str] | None = None,
    ) -> list[str]:
        path = Path(file_path)
        extension = path.suffix.lower()

        logger.info(
            "ingestion_started",
            document_id=document_id,
            file=path.name,
            org_id=self.org_id,
        )

        loader = _get_document_loader(extension, str(path))
        raw_docs = loader.load()
        logger.info("document_loaded", page_count=len(raw_docs))

        splitter = _get_splitter()
        chunks = splitter.split_documents(raw_docs)
        logger.info("document_chunked", chunk_count=len(chunks))

        if not chunks:
            logger.warning("no_chunks_produced", document_id=document_id)
            return []

        texts = [chunk.page_content for chunk in chunks]
        embeddings = await self.llm.embed_batch(texts)

        chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "document_id": document_id,
                "document_title": document_title,
                "org_id": self.org_id,
                "chunk_index": i,
                "source": path.name,
                "tags": ",".join(tags or []),
            }
            for i, chunk in enumerate(chunks)
        ]

        collection = await self.client.get_or_create_collection(
            name=self._collection_name(),
            metadata={"hnsw:space": "cosine"},
        )
        await collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        logger.info(
            "ingestion_complete",
            document_id=document_id,
            chunk_count=len(chunk_ids),
        )
        return chunk_ids

    async def delete_document(self, document_id: str) -> None:
        collection = await self.client.get_or_create_collection(
            name=self._collection_name()
        )
        await collection.delete(where={"document_id": document_id})
        logger.info("document_deleted_from_chroma", document_id=document_id)

    def _collection_name(self) -> str:
        return f"{settings.chroma_collection_name}_{self.org_id}"
