import os
from typing import List, Dict, Any, Optional
import chromadb
from app.core.logger import knowledge_logger
from app.core.config import settings

class MockEmbeddingFunction(chromadb.EmbeddingFunction):
    """Offline, deterministic embedding generator for testing without internet."""
    def __call__(self, input: List[str]) -> List[List[float]]:
        import hashlib
        embeddings = []
        for text in input:
            vector = []
            for i in range(384):
                # Deterministic value using hashlib.md5
                h = hashlib.md5(f"{text}_{i}".encode("utf-8")).hexdigest()
                val = int(h[:8], 16) / 4294967295.0
                vector.append(val)
            norm = sum(x*x for x in vector) ** 0.5
            if norm > 0:
                vector = [x/norm for x in vector]
            embeddings.append(vector)
        return embeddings

    def name(self) -> str:
        return "MockEmbeddingFunction"

class ChromaDBClient:
    """Wrapper around local ChromaDB persistent vector database client."""
    def __init__(self, mock_embeddings: Optional[bool] = None):
        self.chroma_path = str(settings.CHROMA_DIR.resolve())
        # Ensure directories exist
        settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        
        is_mock = mock_embeddings if mock_embeddings is not None else getattr(settings, "MOCK_EMBEDDINGS", False)
        
        try:
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            
            if is_mock:
                self.embedding_function = MockEmbeddingFunction()
                knowledge_logger.info("Using offline MockEmbeddingFunction for ChromaDB.")
            else:
                # Default sentence-transformers/all-MiniLM-L6-v2 embedding function
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
                self.embedding_function = SentenceTransformerEmbeddingFunction()
                
            self.collection = self.client.get_or_create_collection(
                name="taksh_knowledge",
                embedding_function=self.embedding_function
            )
            knowledge_logger.info(f"ChromaDBClient initialized at storage path: {self.chroma_path}")
        except Exception as e:
            knowledge_logger.error(f"Failed to initialize ChromaDBClient: {e}")
            raise RuntimeError(f"ChromaDB failed to initialize: {e}") from e

    def add_chunks(self, document_id: str, filepath: str, chunks: List[Dict[str, Any]]) -> None:
        """Stores document chunk vectors and metadata properties."""
        if not chunks:
            return
            
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            chunk_id = f"{document_id}_{chunk['chunk_index']}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            metadatas.append({
                "document_id": document_id,
                "filepath": filepath,
                "chunk_index": chunk["chunk_index"],
                "heading_hierarchy": ",".join(chunk["heading_hierarchy"]) if chunk.get("heading_hierarchy") else ""
            })
            
        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            knowledge_logger.info(f"Added {len(chunks)} document chunk vectors to collection.")
        except Exception as e:
            knowledge_logger.error(f"Error adding chunks to ChromaDB: {e}")
            raise

    def delete_document_chunks(self, document_id: str) -> None:
        """Purges all vectors matching metadata filter document_id."""
        try:
            self.collection.delete(
                where={"document_id": document_id}
            )
            knowledge_logger.info(f"Deleted chunks for document {document_id} from ChromaDB.")
        except Exception as e:
            knowledge_logger.error(f"Error deleting chunks from ChromaDB: {e}")

    def query_similarity(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Queries local embeddings index for semantically similar passages."""
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=limit
            )
            
            formatted = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                ids = results["ids"][0]
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0] if results.get("distances") else [0.0]*len(ids)
                
                for i in range(len(ids)):
                    formatted.append({
                        "chunk_id": ids[i],
                        "document_id": metadatas[i].get("document_id"),
                        "filepath": metadatas[i].get("filepath"),
                        "content": documents[i],
                        "heading_hierarchy": metadatas[i].get("heading_hierarchy", "").split(",") if metadatas[i].get("heading_hierarchy") else [],
                        "distance": distances[i]
                    })
            return formatted
        except Exception as e:
            knowledge_logger.error(f"Error querying similarity: {e}")
            return []

    def get_collection_count(self) -> int:
        try:
            return self.collection.count()
        except Exception as e:
            knowledge_logger.error(f"Error getting collection count: {e}")
            return 0
