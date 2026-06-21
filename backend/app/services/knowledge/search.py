from typing import List, Dict, Any
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import or_

from app.core.logger import knowledge_logger
from app.services.knowledge.vector_store import ChromaDBClient
from app.models.database_models import KnowledgeChunk, KnowledgeDocument

class HybridSearchEngine:
    """Combines ChromaDB semantic vector search and SQLite lexical keyword search."""
    def __init__(self, chroma_client: ChromaDBClient = None):
        self.chroma_client = chroma_client or ChromaDBClient()
        knowledge_logger.info("HybridSearchEngine initialized.")

    def keyword_search(self, db: DbSession, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Performs lexical search using SQLite LIKE filtering."""
        words = [w.strip() for w in query.split() if len(w.strip()) >= 2]
        if not words:
            # Fallback to single character words if all words are short
            words = [w.strip() for w in query.split() if w.strip()]
            if not words:
                return []

        clauses = [KnowledgeChunk.content.like(f"%{word}%") for word in words]
        
        try:
            chunks = db.query(KnowledgeChunk).join(KnowledgeDocument).filter(
                or_(*clauses)
            ).limit(limit).all()
            
            formatted = []
            for chunk in chunks:
                chunk_id = f"{chunk.document_id}_{chunk.chunk_index}"
                formatted.append({
                    "chunk_id": chunk_id,
                    "document_id": chunk.document_id,
                    "filepath": chunk.document.filepath,
                    "content": chunk.content,
                    "heading_hierarchy": chunk.heading_hierarchy
                })
            return formatted
        except Exception as e:
            knowledge_logger.error(f"Error during keyword search: {e}")
            return []

    def reciprocal_rank_fusion(
        self, 
        vector_results: List[Dict[str, Any]], 
        keyword_results: List[Dict[str, Any]], 
        k: int = 60, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Merges and reranks results using Reciprocal Rank Fusion (RRF)."""
        scores = {}
        
        # Merge vector results
        for rank, res in enumerate(vector_results):
            chunk_id = res["chunk_id"]
            if chunk_id not in scores:
                scores[chunk_id] = {"item": dict(res), "score": 0.0}
            scores[chunk_id]["score"] += 1.0 / (k + (rank + 1))
            
        # Merge keyword results
        for rank, res in enumerate(keyword_results):
            chunk_id = res["chunk_id"]
            if chunk_id not in scores:
                scores[chunk_id] = {"item": dict(res), "score": 0.0}
            scores[chunk_id]["score"] += 1.0 / (k + (rank + 1))
            
        # Sort by score descending
        sorted_results = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        
        merged = []
        for s in sorted_results[:limit]:
            item = s["item"]
            item["score"] = s["score"]
            item.pop("distance", None) # Remove raw distance if present
            merged.append(item)
            
        return merged

    def search(self, db: DbSession, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Executes hybrid retrieval: semantic similarity & syntactic keyword matching, reranking candidates."""
        knowledge_logger.info(f"Initiating hybrid search for query: '{query}'")
        
        # Query twice the limit to ensure adequate candidate pool for RRF
        candidate_limit = max(limit * 2, 10)
        
        # 1. Vector Search
        vector_results = self.chroma_client.query_similarity(query, limit=candidate_limit)
        
        # 2. Keyword Search
        keyword_results = self.keyword_search(db, query, limit=candidate_limit)
        
        # 3. Reciprocal Rank Fusion
        merged_results = self.reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            k=60,
            limit=limit
        )
        
        knowledge_logger.info(f"Hybrid search completed. Reranked {len(merged_results)} results.")
        return merged_results
