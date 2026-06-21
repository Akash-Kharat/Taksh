import re
from typing import List, Dict, Any
from app.core.logger import knowledge_logger
from app.core.config import settings

class MarkdownStructureParser:
    """Structure-aware markdown parser and chunker.
    
    Splits files based on markdown headers, retaining structure metadata.
    """
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or settings.KNOWLEDGE_CHUNK_SIZE
        self.overlap = overlap or settings.KNOWLEDGE_CHUNK_OVERLAP
        knowledge_logger.info(f"MarkdownStructureParser initialized with chunk_size={self.chunk_size}, overlap={self.overlap}.")

    def parse_document(self, filepath: str) -> List[Dict[str, Any]]:
        """Reads document and creates semantic chunks with header trees metadata."""
        knowledge_logger.info(f"Parsing document filepath: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            knowledge_logger.error(f"Failed to read file {filepath}: {e}")
            return []

        # Split content into lines
        lines = content.splitlines()
        
        # Track parent headers stack: elements are tuples of (level, title)
        header_stack = []
        chunks = []
        current_chunk_lines = []
        current_hierarchy = []
        
        def get_hierarchy_list(stack):
            return [h[1] for h in stack]
            
        def clean_header(header_text):
            return re.sub(r'^#+\s+', '', header_text).strip()
            
        for line in lines:
            # Check if line is a header
            match = re.match(r'^(#{1,6})\s+(.*)$', line)
            if match:
                # We found a header. We should save the current chunk first (if any).
                if current_chunk_lines:
                    chunk_text = "\n".join(current_chunk_lines).strip()
                    if chunk_text:
                        chunks.append({
                            "content": chunk_text,
                            "heading_hierarchy": list(current_hierarchy)
                        })
                    current_chunk_lines = []
                
                level = len(match.group(1))
                title = clean_header(line)
                
                # Pop headers from stack that are at same or deeper level
                while header_stack and header_stack[-1][0] >= level:
                    header_stack.pop()
                
                header_stack.append((level, title))
                current_hierarchy = get_hierarchy_list(header_stack)
                
                # Include the header line in the next chunk
                current_chunk_lines.append(line)
            else:
                current_chunk_lines.append(line)
                
        # Append final chunk if any
        if current_chunk_lines:
            chunk_text = "\n".join(current_chunk_lines).strip()
            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "heading_hierarchy": list(current_hierarchy)
                })

        # Apply chunk size splitting with overlap
        refined_chunks = []
        for c in chunks:
            text = c["content"]
            words = text.split()
            if len(words) <= self.chunk_size:
                refined_chunks.append(c)
            else:
                i = 0
                while i < len(words):
                    sub_words = words[i:i + self.chunk_size]
                    sub_text = " ".join(sub_words)
                    refined_chunks.append({
                        "content": sub_text,
                        "heading_hierarchy": c["heading_hierarchy"]
                    })
                    i += max(1, self.chunk_size - self.overlap)
                    
        # Add chunk index to each chunk
        for index, rc in enumerate(refined_chunks):
            rc["chunk_index"] = index

        return refined_chunks
