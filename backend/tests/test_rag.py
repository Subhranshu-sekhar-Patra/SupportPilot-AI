"""
SupportPilot AI — Comprehensive RAG & Document Ingestion Test Suite
Tests:
- PyMuPDF PDF text extraction
- python-docx Word text extraction
- Text cleaning and normalization
- Corrupted / unsupported file handling
- LangChain chunking with metadata preservation
- ChromaDB vector storage and semantic cosine similarity retrieval
- Sample company policies demonstration (Refund Policy, SLA Policy)
- Strict multi-tenant isolation in RAG retrieval
- Document re-indexing and deletion lifecycle
"""

import os
import tempfile
import fitz  # PyMuPDF
import docx
import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.providers.embeddings import LocalDeterministicEmbeddingProvider
from app.ai.rag.ingestion import DocumentIngestionService
from app.ai.rag.retrieval import RetrievalService
from app.ai.rag.text_extractor import DocumentTextExtractor, clean_text
from app.core.exceptions import ValidationError
from app.main import app


# ── Sample Enterprise Policies for RAG Demonstration ──────────

SAMPLE_REFUND_POLICY = """
SupportPilot Enterprise — Refund and Subscription Cancellation Policy (2026)

1. 30-Day Money-Back Guarantee
All new annual enterprise subscriptions are covered by our 30-day no-questions-asked refund policy.
If the customer submits a refund request within 30 calendar days from the initial payment date,
SupportPilot will issue a 100% full refund to the original payment method (Stripe or Wire Transfer).

2. One-Time Setup and Custom Migration Fees
One-time professional onboarding fees, custom AI model fine-tuning services, and architectural
migration retainers are non-refundable once engineering delivery has commenced.

3. Mid-Term Cancellation and Pro-Rated Credits
Cancellations requested after the 30-day window will terminate at the conclusion of the active
billing term. We provide pro-rated platform credits applicable toward future billing cycles upon
written approval from the Finance Operations team.
"""

SAMPLE_SLA_POLICY = """
SupportPilot Enterprise — Service Level Agreement (SLA) & Incident Management

1. Platform Availability Commitment
SupportPilot guarantees 99.95% monthly service availability for core API endpoints, live chat
gateways, and webhook dispatch engines, excluding scheduled maintenance windows notified 72 hours in advance.

2. Incident Priority Matrix and Response Times
- Priority 1 (Urgent / Outage): Critical business blocker affecting >= 25% of users.
  Guaranteed First Response Time: 15 minutes. Updates every 30 minutes.
- Priority 2 (High / Degraded): Major feature failure with reasonable workaround.
  Guaranteed First Response Time: 60 minutes. Updates every 2 hours.
- Priority 3 (Medium / Normal): General inquiry, cosmetic bug, or non-blocking issue.
  Guaranteed First Response Time: 4 hours.

3. Service Credits for SLA Breaches
If monthly availability drops below 99.95%, enterprise customers are entitled to a 10% credit.
For uptime below 99.0%, customers are entitled to a 25% credit applied to the next billing invoice.
"""


def test_text_cleaning_and_normalization():
    """Verify clean_text normalizes unicode, collapses whitespace, and strips control characters."""
    dirty = "SupportPilot   AI\r\n\r\n\n\nPlatform   Features \xa0\xa0 Guarantee\x00\x08"
    cleaned = clean_text(dirty)
    assert "SupportPilot AI" in cleaned
    assert "Platform Features" in cleaned
    assert "Guarantee" in cleaned
    assert "\x00" not in cleaned
    assert "\n\n\n" not in cleaned


def test_pdf_extraction_with_pymupdf():
    """Verify PyMuPDF successfully extracts text from a rendered PDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Create a real PDF using PyMuPDF (fitz)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "SupportPilot AI — Enterprise Security Runbook\nConfidential DPA 2026")
        doc.save(tmp_path)
        doc.close()

        extracted = DocumentTextExtractor.extract(tmp_path)
        assert "SupportPilot AI" in extracted
        assert "Enterprise Security Runbook" in extracted
        assert "Confidential DPA 2026" in extracted
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_docx_extraction_with_python_docx():
    """Verify python-docx extracts paragraphs and tables from a Word document."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Create a real DOCX
        doc = docx.Document()
        doc.add_heading("Okta SAML SSO Configuration", level=1)
        doc.add_paragraph("Configure the ACS URL and Entity ID in the SupportPilot admin console.")
        table = doc.add_table(rows=2, cols=2)
        table.rows[0].cells[0].text = "Setting"
        table.rows[0].cells[1].text = "Value"
        table.rows[1].cells[0].text = "SAML Endpoint"
        table.rows[1].cells[1].text = "https://app.supportpilot.io/saml/sso"
        doc.save(tmp_path)

        extracted = DocumentTextExtractor.extract(tmp_path)
        assert "Okta SAML SSO Configuration" in extracted
        assert "Entity ID" in extracted
        assert "https://app.supportpilot.io/saml/sso" in extracted
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_corrupted_file_handling():
    """Verify corrupted files trigger a ValidationError."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"NOT_A_REAL_PDF_CORRUPTED_BYTES_123456789")
        tmp_path = tmp.name

    try:
        with pytest.raises(ValidationError):
            DocumentTextExtractor.extract(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.anyio
async def test_rag_semantic_search_with_company_policies():
    """
    Demonstrate RAG with real enterprise policies:
    1. Ingest Refund Policy and SLA Policy
    2. Query for refund timelines -> Top hit is Refund Policy
    3. Query for P1 response times -> Top hit is SLA Policy
    """
    org_id = f"test_org_rag_{hash('policies')}"
    embedder = LocalDeterministicEmbeddingProvider()
    ingestor = DocumentIngestionService(embedder, org_id)
    retriever = RetrievalService(embedder, org_id)

    # 1. Write sample policy files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f1:
        f1.write(SAMPLE_REFUND_POLICY)
        refund_path = f1.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f2:
        f2.write(SAMPLE_SLA_POLICY)
        sla_path = f2.name

    try:
        # 2. Ingest policies
        refund_chunks = await ingestor.ingest_file(
            file_path=refund_path,
            document_id="doc_refund_001",
            document_title="Enterprise Refund & Cancellation Policy",
            tags=["billing", "refunds", "finance"],
        )
        assert len(refund_chunks) >= 1

        sla_chunks = await ingestor.ingest_file(
            file_path=sla_path,
            document_id="doc_sla_002",
            document_title="Enterprise SLA & Incident Management",
            tags=["sla", "incidents", "support"],
        )
        assert len(sla_chunks) >= 1

        # 3. Query 1: Refund window question
        query_refund = "What is the refund window for new annual enterprise subscriptions?"
        results_refund = await retriever.retrieve(query_refund, top_k=2)
        assert len(results_refund) >= 1
        top_refund = results_refund[0]
        assert top_refund.document_id == "doc_refund_001"
        assert "30-Day Money-Back Guarantee" in top_refund.content
        assert top_refund.similarity_score > 0.3

        # 4. Query 2: SLA response time question
        query_sla = "What is the guaranteed first response time for a P1 urgent incident?"
        results_sla = await retriever.retrieve(query_sla, top_k=2)
        assert len(results_sla) >= 1
        top_sla = results_sla[0]
        assert top_sla.document_id == "doc_sla_002"
        assert "15 minutes" in top_sla.content
        assert top_sla.similarity_score > 0.3

    finally:
        await ingestor.delete_document("doc_refund_001")
        await ingestor.delete_document("doc_sla_002")
        if os.path.exists(refund_path):
            os.remove(refund_path)
        if os.path.exists(sla_path):
            os.remove(sla_path)


@pytest.mark.anyio
async def test_strict_multi_tenant_rag_isolation():
    """
    CRITICAL SECURITY TEST:
    Verify that an organization can NEVER retrieve vectors from another organization.
    """
    org_alpha = f"org_alpha_{hash('tenant_a')}"
    org_beta = f"org_beta_{hash('tenant_b')}"

    embedder = LocalDeterministicEmbeddingProvider()
    ingestor_a = DocumentIngestionService(embedder, org_alpha)
    retriever_b = RetrievalService(embedder, org_beta)

    # Org Alpha uploads a proprietary strategy document
    secret_text = "Project Starlight: Alpha Corporation plan to acquire TechScale Inc for $450M in Q3 2026."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(secret_text)
        secret_path = f.name

    try:
        await ingestor_a.ingest_file(
            file_path=secret_path,
            document_id="doc_secret_alpha",
            document_title="M&A Acquisition Strategy",
        )

        # Org Beta searches for the secret M&A plan -> MUST RETURN 0 CHUNKS
        results_for_beta = await retriever_b.retrieve("acquire TechScale Inc M&A plan", top_k=5)
        assert len(results_for_beta) == 0

    finally:
        await ingestor_a.delete_document("doc_secret_alpha")
        if os.path.exists(secret_path):
            os.remove(secret_path)


@pytest.mark.anyio
async def test_api_knowledge_endpoints_end_to_end():
    """Verify document upload, listing, semantic querying, re-indexing, and deletion via HTTP API."""
    from app.core.middleware import reset_rate_limiters
    reset_rate_limiters()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"rag_lead_{hash('rag_api')}@defense.com",
                "password": "Password123!",
                "full_name": "Major Samantha Carter",
                "organization_name": "Stargate Command",
            },
        )
        token = reg_res.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Upload a Markdown document
        doc_content = b"# Stargate Dialing Protocol\n\nEngage chevron 1 through 7 to establish wormhole connection."
        files = {
            "file": ("dialing_protocol.md", doc_content, "text/markdown"),
        }
        data = {
            "title": "Stargate Dialing Protocol",
            "tags": "wormholes,defense,protocols",
            "is_async": "false",
        }

        upload_res = await client.post(
            "/api/v1/knowledge/upload",
            headers=headers,
            files=files,
            data=data,
        )
        assert upload_res.status_code == 201
        uploaded_doc = upload_res.json()
        doc_id = uploaded_doc["id"]
        assert uploaded_doc["status"].lower() == "indexed"
        assert uploaded_doc["chunk_count"] >= 1

        # 2. List documents
        list_res = await client.get("/api/v1/knowledge", headers=headers)
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

        # 3. Query knowledge base via API
        query_res = await client.post(
            "/api/v1/knowledge/query",
            headers=headers,
            json={"query": "How many chevrons are engaged for dialing?", "top_k": 3},
        )
        assert query_res.status_code == 200
        query_data = query_res.json()
        assert query_data["total_found"] >= 1
        assert "chevron 1 through 7" in query_data["results"][0]["content"]

        # 4. Reindex document
        reindex_res = await client.post(
            f"/api/v1/knowledge/{doc_id}/reindex", headers=headers
        )
        assert reindex_res.status_code == 200
        assert reindex_res.json()["status"].lower() == "indexed"

        # 5. Delete document
        del_res = await client.delete(f"/api/v1/knowledge/{doc_id}", headers=headers)
        assert del_res.status_code == 204

        # 6. Verify deleted
        get_res = await client.get(f"/api/v1/knowledge/{doc_id}", headers=headers)
        assert get_res.status_code == 404
