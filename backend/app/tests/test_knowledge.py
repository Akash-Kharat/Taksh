import os
import pytest
from pathlib import Path
from sqlalchemy.orm import Session as DbSession
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.knowledge.parser import MarkdownStructureParser
from app.services.knowledge.vector_store import ChromaDBClient
from app.services.knowledge.ingestion import IngestionService, KnowledgeIngestionLock
from app.services.knowledge.search import HybridSearchEngine
from app.models.database_models import KnowledgeDocument, KnowledgeChunk, KnowledgeIngestionMetrics


def test_markdown_structure_parser(tmp_path):
    # Create a dummy markdown file
    dummy_content = """# Vision
This is the vision block.
## Trust Model
This is the trust model sub-block.
"""
    test_file = tmp_path / "test_doc.md"
    test_file.write_text(dummy_content, encoding="utf-8")

    parser = MarkdownStructureParser(chunk_size=10, overlap=2)
    chunks = parser.parse_document(str(test_file))

    # Expecting 2 chunks
    assert len(chunks) == 2
    assert chunks[0]["heading_hierarchy"] == ["Vision"]
    assert "vision" in chunks[0]["content"].lower()
    assert chunks[1]["heading_hierarchy"] == ["Vision", "Trust Model"]
    assert "trust" in chunks[1]["content"].lower()


def test_chroma_db_client():
    # ChromaDBClient uses mock embeddings since conftest.py sets MOCK_EMBEDDINGS = True
    client = ChromaDBClient()
    doc_id = "test_doc_123"
    filepath = "Vision/test_doc.md"
    chunks = [
        {"chunk_index": 0, "content": "Hello world from Chroma", "heading_hierarchy": ["Vision", "Intro"]},
        {"chunk_index": 1, "content": "Second paragraph of the doc", "heading_hierarchy": ["Vision", "Details"]}
    ]

    # Add chunks
    client.add_chunks(doc_id, filepath, chunks)
    assert client.get_collection_count() >= 2

    # Query similarity
    results = client.query_similarity("Hello world", limit=2)
    assert len(results) >= 1
    assert any("Hello world" in r["content"] for r in results)

    # Delete chunks
    client.delete_document_chunks(doc_id)
    # The count should decrease or remain 0 if cleared
    query_after = client.query_similarity("Hello world", limit=2)
    assert not any(r["document_id"] == doc_id for r in query_after)


def test_ingestion_lock():
    assert not KnowledgeIngestionLock.is_running()
    
    # Acquire
    success = KnowledgeIngestionLock.acquire()
    assert success
    assert KnowledgeIngestionLock.is_running()

    # Re-acquire should fail
    success_again = KnowledgeIngestionLock.acquire()
    assert not success_again

    # Release
    KnowledgeIngestionLock.release()
    assert not KnowledgeIngestionLock.is_running()


def test_ingestion_service(db_session, tmp_path):
    # Set DOCS_DIR to temporary path
    original_docs_dir = settings.DOCS_DIR
    settings.DOCS_DIR = tmp_path
    
    try:
        # Create allowed subdirectories
        vision_dir = tmp_path / "Vision"
        vision_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Test Ingestion with a new file
        file_a = vision_dir / "identity.md"
        file_a.write_text("# Socratic Identity\nTaksh is a voice-enabled engineering mentor.", encoding="utf-8")
        
        chroma = ChromaDBClient()
        service = IngestionService(db_session, chroma_client=chroma)
        
        res = service.run_ingestion()
        assert res["status"] == "completed"
        assert res["metrics"]["indexed_documents"] == 1
        assert res["metrics"]["skipped_documents"] == 0
        assert res["metrics"]["total_documents"] == 1
        
        # Verify db persistence
        db_doc = db_session.query(KnowledgeDocument).filter(KnowledgeDocument.filepath == "Vision/identity.md").first()
        assert db_doc is not None
        assert db_session.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == db_doc.document_id).count() == 1

        # 2. Test Ingestion with no changes (Skipped)
        res_skip = service.run_ingestion()
        assert res_skip["metrics"]["skipped_documents"] == 1
        assert res_skip["metrics"]["indexed_documents"] == 0
        
        # 3. Test Ingestion with modifications (Reindexed)
        file_a.write_text("# Socratic Identity\nTaksh is a voice-enabled engineering mentor. Now with more details.", encoding="utf-8")
        res_mod = service.run_ingestion()
        assert res_mod["metrics"]["reindexed_documents"] == 1
        assert res_mod["metrics"]["skipped_documents"] == 0
        
        # 4. Test Ingestion with file deletion
        file_a.unlink()
        res_del = service.run_ingestion()
        assert res_del["metrics"]["deleted_documents"] == 1
        assert db_session.query(KnowledgeDocument).count() == 0
        
    finally:
        settings.DOCS_DIR = original_docs_dir


def test_hybrid_search_rrf(db_session, tmp_path):
    # Set setup and ingest mock records
    doc = KnowledgeDocument(filepath="Architecture/test.md", file_hash="abc")
    db_session.add(doc)
    db_session.flush()
    
    chunk = KnowledgeChunk(
        document_id=doc.document_id,
        chunk_index=0,
        content="FreeRTOS task notifications are faster than semaphores.",
        heading_hierarchy=["Architecture", "FreeRTOS"]
    )
    db_session.add(chunk)
    db_session.commit()
    
    # Push to mock ChromaDB
    chroma = ChromaDBClient()
    chroma.add_chunks(doc.document_id, doc.filepath, [
        {"chunk_index": 0, "content": "FreeRTOS task notifications are faster than semaphores.", "heading_hierarchy": ["Architecture", "FreeRTOS"]}
    ])
    
    search_engine = HybridSearchEngine(chroma_client=chroma)
    
    # Test keyword search
    kw_results = search_engine.keyword_search(db_session, "FreeRTOS task")
    assert len(kw_results) >= 1
    assert "FreeRTOS" in kw_results[0]["content"]
    
    # Test RRF search
    results = search_engine.search(db_session, "FreeRTOS semaphores", limit=2)
    assert len(results) >= 1
    assert "score" in results[0]
    assert results[0]["filepath"] == "Architecture/test.md"


def test_knowledge_api_endpoints(client, db_session, tmp_path):
    original_docs_dir = settings.DOCS_DIR
    settings.DOCS_DIR = tmp_path
    
    try:
        # 1. Ingestion Info API (empty)
        response = client.get("/api/v1/knowledge/info")
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 0
        assert data["total_chunks"] == 0

        # Create dummy structure
        vision_dir = tmp_path / "Vision"
        vision_dir.mkdir(parents=True, exist_ok=True)
        file_a = vision_dir / "test.md"
        file_a.write_text("# Title\nThis is dummy content for testing endpoints.", encoding="utf-8")

        # 2. Trigger Ingestion API
        response = client.post("/api/v1/knowledge/ingest")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["queued", "already_running"]
        
        # Run synchronous ingestion so DB has data for search/document queries
        chroma = ChromaDBClient()
        service = IngestionService(db_session, chroma_client=chroma)
        service.run_ingestion()

        # Check Info after Ingestion
        response = client.get("/api/v1/knowledge/info")
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 1
        assert data["indexed_documents"] in [0, 1]

        # Query Document ID
        doc = db_session.query(KnowledgeDocument).first()
        assert doc is not None

        # 3. Document Retrieval API
        response = client.get(f"/api/v1/knowledge/document/{doc.document_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["filepath"] == "Vision/test.md"
        assert len(data["chunks"]) == 1

        # 4. Search API
        response = client.get("/api/v1/knowledge/search?query=dummy")
        assert response.status_code == 200
        results = response.json()
        assert len(results) >= 1
        assert "dummy" in results[0]["content"].lower()

    finally:
        settings.DOCS_DIR = original_docs_dir
