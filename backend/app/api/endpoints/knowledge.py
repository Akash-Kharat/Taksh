from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db, SessionLocal
from app.core.logger import api_logger, knowledge_logger
from app.services.knowledge.ingestion import IngestionService, KnowledgeIngestionLock
from app.services.knowledge.search import HybridSearchEngine
from app.models.database_models import KnowledgeDocument, KnowledgeIngestionMetrics
from app.schemas.knowledge import (
    KnowledgeSearchResponse,
    KnowledgeInfoResponse,
    KnowledgeDocumentDetailResponse,
    KnowledgeIngestResponse
)

router = APIRouter()

@router.post("/knowledge/ingest", response_model=KnowledgeIngestResponse)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    api_logger.info("Received request to trigger workspace RAG ingestion")
    
    if KnowledgeIngestionLock.is_running():
        knowledge_logger.warning("Ingestion requested but already running.")
        return {
            "status": "already_running",
            "message": "Knowledge ingestion is currently in progress."
        }

    def run_ingestion_in_background():
        with SessionLocal() as db:
            service = IngestionService(db)
            service.run_ingestion()

    background_tasks.add_task(run_ingestion_in_background)
    return {
        "status": "queued",
        "message": "Workspace ingestion triggered successfully in the background."
    }

@router.get("/knowledge/search", response_model=List[KnowledgeSearchResponse])
def search_knowledge(
    query: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=50),
    db: DbSession = Depends(get_db)
):
    search_engine = HybridSearchEngine()
    results = search_engine.search(db, query, limit=limit)
    return results

@router.get("/knowledge/info", response_model=KnowledgeInfoResponse)
def get_knowledge_info(db: DbSession = Depends(get_db)):
    # Retrieve the latest run metrics
    latest_metrics = db.query(KnowledgeIngestionMetrics).order_by(
        KnowledgeIngestionMetrics.id.desc()
    ).first()
    
    if not latest_metrics:
        # Default empty counts
        return {
            "total_documents": db.query(KnowledgeDocument).count(),
            "total_chunks": 0,
            "indexed_documents": 0,
            "skipped_documents": 0,
            "reindexed_documents": 0,
            "deleted_documents": 0,
            "last_ingested_at": None
        }

    return latest_metrics

@router.get("/knowledge/document/{document_id}", response_model=KnowledgeDocumentDetailResponse)
def get_knowledge_document(document_id: str, db: DbSession = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
