from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class KnowledgeChunkResponse(BaseModel):
    chunk_id: str
    chunk_index: int
    heading_hierarchy: List[str]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class KnowledgeDocumentDetailResponse(BaseModel):
    document_id: str
    filepath: str
    file_hash: str
    created_at: datetime
    updated_at: datetime
    chunks: List[KnowledgeChunkResponse]

    model_config = ConfigDict(from_attributes=True)

class KnowledgeSearchResponse(BaseModel):
    chunk_id: str
    document_id: str
    filepath: str
    heading_hierarchy: List[str]
    content: str
    score: float

    model_config = ConfigDict(from_attributes=True)

class KnowledgeInfoResponse(BaseModel):
    total_documents: int
    total_chunks: int
    indexed_documents: int
    skipped_documents: int
    reindexed_documents: int
    deleted_documents: int
    last_ingested_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class KnowledgeIngestResponse(BaseModel):
    status: str
    message: str
    metrics: Optional[KnowledgeInfoResponse] = None
