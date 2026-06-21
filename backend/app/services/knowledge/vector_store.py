from typing import List, Dict, Any
from app.core.logger import knowledge_logger
from app.core.config import settings

class ChromaDBClient:
    """Wrapper around local ChromaDB persistent vector database client."""
    def __init__(self):
        self.chroma_path = settings.CHROMA_DIR
        knowledge_logger.info(f"ChromaDBClient initialized at storage path: {self.chroma_path}")

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Stores document chunk vectors and metadata properties."""
        knowledge_logger.info(f"Adding {len(documents)} document chunk vectors to vector collection")

    def query_similarity(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Queries local embeddings index for semantically similar passages."""
        knowledge_logger.debug(f"Executing semantic similarity query: '{query_text}'")
        return []
