import os
import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.logger import knowledge_logger
from app.models.database_models import KnowledgeDocument, KnowledgeChunk, KnowledgeIngestionMetrics
from app.services.knowledge.parser import MarkdownStructureParser
from app.services.knowledge.vector_store import ChromaDBClient

class KnowledgeIngestionLock:
    """Thread-safe and async-safe lock for knowledge ingestion jobs."""
    _lock = threading.Lock()
    _is_running = False

    @classmethod
    def acquire(cls) -> bool:
        with cls._lock:
            if cls._is_running:
                return False
            cls._is_running = True
            return True

    @classmethod
    def release(cls) -> None:
        with cls._lock:
            cls._is_running = False

    @classmethod
    def is_running(cls) -> bool:
        with cls._lock:
            return cls._is_running


def calculate_sha256(filepath: Path) -> str:
    """Calculates SHA-256 hash of a file's content."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        knowledge_logger.error(f"Failed to calculate hash for {filepath}: {e}")
        return ""


class IngestionService:
    """Manages markdown documents ingestion, incremental reindexing, and vector sync."""
    
    def __init__(self, db: DbSession, chroma_client: ChromaDBClient = None):
        self.db = db
        self.chroma_client = chroma_client or ChromaDBClient()
        self.parser = MarkdownStructureParser()
        self.allowed_subdirs = ["Vision", "Architecture", "ADR", "Skills", "Roadmaps", "Research"]

    def get_markdown_files(self) -> Dict[str, Path]:
        """Scans the allowed docs subdirectories recursively for markdown files."""
        docs_dir = settings.DOCS_DIR
        markdown_files = {}

        if not docs_dir.exists():
            knowledge_logger.error(f"Docs directory {docs_dir} does not exist.")
            return markdown_files

        for subdir in self.allowed_subdirs:
            subdir_path = docs_dir / subdir
            if subdir_path.exists() and subdir_path.is_dir():
                for p in subdir_path.rglob("*.md"):
                    # Use a normalized relative path representation
                    try:
                        rel_path = p.relative_to(docs_dir).as_posix()
                        markdown_files[rel_path] = p
                    except Exception as e:
                        knowledge_logger.error(f"Error resolving path for {p}: {e}")
        return markdown_files

    def run_ingestion(self) -> Dict[str, Any]:
        """Performs incremental ingestion of markdown files."""
        if not KnowledgeIngestionLock.acquire():
            knowledge_logger.warning("Ingestion process is already running. Skipping.")
            return {"status": "already_running"}

        metrics = {
            "total_documents": 0,
            "total_chunks": 0,
            "indexed_documents": 0,
            "skipped_documents": 0,
            "reindexed_documents": 0,
            "deleted_documents": 0,
            "last_ingested_at": datetime.utcnow()
        }

        try:
            knowledge_logger.info("Starting knowledge ingestion pipeline...")
            
            # 1. Scan filesystem
            disk_files = self.get_markdown_files()
            
            # 2. Query database for existing documents
            db_docs = self.db.query(KnowledgeDocument).all()
            db_docs_dict = {doc.filepath: doc for doc in db_docs}

            # Set of files processed or active
            active_filepaths = set(disk_files.keys())

            # 3. Process additions and modifications
            for rel_path, file_path in disk_files.items():
                current_hash = calculate_sha256(file_path)
                if not current_hash:
                    continue

                db_doc = db_docs_dict.get(rel_path)

                if not db_doc:
                    # New Document
                    knowledge_logger.info(f"New document detected: {rel_path}")
                    self._ingest_new_document(rel_path, file_path, current_hash)
                    metrics["indexed_documents"] += 1
                elif db_doc.file_hash != current_hash:
                    # Modified Document
                    knowledge_logger.info(f"Modified document detected: {rel_path}")
                    self._reindex_document(db_doc, file_path, current_hash)
                    metrics["reindexed_documents"] += 1
                else:
                    # Unmodified
                    metrics["skipped_documents"] += 1

            # 4. Process deletions
            for rel_path, db_doc in db_docs_dict.items():
                if rel_path not in active_filepaths:
                    knowledge_logger.info(f"Deleted document detected: {rel_path}")
                    self._delete_document(db_doc)
                    metrics["deleted_documents"] += 1

            # 5. Populate totals
            total_docs = self.db.query(KnowledgeDocument).count()
            total_chunks = self.db.query(KnowledgeChunk).count()
            metrics["total_documents"] = total_docs
            metrics["total_chunks"] = total_chunks

            # Save metrics to DB
            run_metrics = KnowledgeIngestionMetrics(
                total_documents=metrics["total_documents"],
                total_chunks=metrics["total_chunks"],
                indexed_documents=metrics["indexed_documents"],
                skipped_documents=metrics["skipped_documents"],
                reindexed_documents=metrics["reindexed_documents"],
                deleted_documents=metrics["deleted_documents"],
                last_ingested_at=metrics["last_ingested_at"]
            )
            self.db.add(run_metrics)
            self.db.commit()

            knowledge_logger.info("Knowledge ingestion pipeline completed successfully.")
            return {
                "status": "completed",
                "metrics": metrics
            }

        except Exception as e:
            self.db.rollback()
            knowledge_logger.exception(f"Exception during knowledge ingestion: {e}")
            return {"status": "failed", "error": str(e)}

        finally:
            KnowledgeIngestionLock.release()

    def _ingest_new_document(self, filepath: str, file_path: Path, file_hash: str) -> None:
        # Create KnowledgeDocument
        doc = KnowledgeDocument(
            filepath=filepath,
            file_hash=file_hash
        )
        self.db.add(doc)
        self.db.flush() # Populate doc.document_id

        # Parse document
        chunks = self.parser.parse_document(str(file_path.resolve()))
        
        # Save chunks in SQLite
        db_chunks = []
        for c in chunks:
            chunk = KnowledgeChunk(
                document_id=doc.document_id,
                chunk_index=c["chunk_index"],
                content=c["content"],
                heading_hierarchy=c["heading_hierarchy"]
            )
            self.db.add(chunk)
            db_chunks.append(chunk)

        self.db.flush()

        # Save to ChromaDB
        self.chroma_client.add_chunks(doc.document_id, filepath, chunks)
        self.db.commit()

    def _reindex_document(self, doc: KnowledgeDocument, file_path: Path, file_hash: str) -> None:
        # Delete old chunks from SQLite
        self.db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.document_id).delete()
        
        # Delete old chunks from ChromaDB
        self.chroma_client.delete_document_chunks(doc.document_id)
        
        # Update hash
        doc.file_hash = file_hash
        doc.updated_at = datetime.utcnow()
        self.db.flush()

        # Parse and save new chunks
        chunks = self.parser.parse_document(str(file_path.resolve()))
        db_chunks = []
        for c in chunks:
            chunk = KnowledgeChunk(
                document_id=doc.document_id,
                chunk_index=c["chunk_index"],
                content=c["content"],
                heading_hierarchy=c["heading_hierarchy"]
            )
            self.db.add(chunk)
            db_chunks.append(chunk)
            
        self.db.flush()

        # Save to ChromaDB
        self.chroma_client.add_chunks(doc.document_id, doc.filepath, chunks)
        self.db.commit()

    def _delete_document(self, doc: KnowledgeDocument) -> None:
        # Cascade will delete SQLite chunks, but delete from ChromaDB first
        self.chroma_client.delete_document_chunks(doc.document_id)
        self.db.delete(doc)
        self.db.commit()
