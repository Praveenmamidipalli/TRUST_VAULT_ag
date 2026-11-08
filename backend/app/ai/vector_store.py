import re
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class DocumentChunk:
    def __init__(self, document_id: int, chunk_id: int, text: str, page_number: Optional[int] = None):
        self.document_id = document_id
        self.chunk_id = chunk_id
        self.text = text
        self.page_number = page_number


class VectorStore:
    """In-memory vector store with deterministic, authorization-bounded similarity search.
    
    Security Guarantee:
    - Queries are mathematically partitioned by authorized_document_ids.
    - Chunks belonging to unauthorized documents NEVER enter the similarity candidate set.
    """

    def __init__(self):
        self.chunks: List[DocumentChunk] = []

    def chunk_text(self, document_id: int, text: str, chunk_size: int = 500, overlap: int = 100) -> List[DocumentChunk]:
        """Splits document text into overlapping chunks."""
        # Remove existing chunks for this document if re-indexing
        self.delete_document_chunks(document_id)

        if not text or not text.strip():
            return []

        # Parse pages if present
        pages = re.split(r"--- Page (\d+) ---", text)
        created_chunks = []
        chunk_idx = 0

        if len(pages) > 1:
            for i in range(1, len(pages), 2):
                page_num = int(pages[i])
                page_content = pages[i + 1].strip()
                start = 0
                while start < len(page_content):
                    end = start + chunk_size
                    chunk_text = page_content[start:end].strip()
                    if chunk_text:
                        chunk = DocumentChunk(document_id, chunk_idx, chunk_text, page_number=page_num)
                        created_chunks.append(chunk)
                        chunk_idx += 1
                    start += chunk_size - overlap
        else:
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunk = DocumentChunk(document_id, chunk_idx, chunk_text)
                    created_chunks.append(chunk)
                    chunk_idx += 1
                start += chunk_size - overlap

        self.chunks.extend(created_chunks)
        return created_chunks

    def delete_document_chunks(self, document_id: int) -> None:
        """Removes all indexed chunks for a document."""
        self.chunks = [c for c in self.chunks if c.document_id != document_id]

    def search(
        self,
        query: str,
        authorized_document_ids: List[int],
        top_k: int = 5,
        min_similarity: float = 0.05
    ) -> List[Dict[str, Any]]:
        """Performs similarity retrieval strictly bounded by authorized_document_ids.
        
        Security Rule:
        - If authorized_document_ids is empty, returns empty list immediately.
        - Chunks from unpermitted documents are excluded prior to vector ranking.
        """
        if not authorized_document_ids or not self.chunks or not query.strip():
            return []

        # Filter candidate chunks to ONLY authorized documents
        permitted_chunks = [c for c in self.chunks if c.document_id in authorized_document_ids]
        if not permitted_chunks:
            return []

        # Build corpus with candidate chunks + query
        corpus = [c.text for c in permitted_chunks]
        corpus.append(query)

        try:
            vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True)
            tfidf_matrix = vectorizer.fit_transform(corpus)

            # Query vector is the last row
            query_vector = tfidf_matrix[-1]
            chunk_vectors = tfidf_matrix[:-1]

            # Compute cosine similarity
            sims = cosine_similarity(query_vector, chunk_vectors).flatten()

            results = []
            for idx, score in enumerate(sims):
                if score >= min_similarity:
                    chunk = permitted_chunks[idx]
                    results.append({
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.chunk_id,
                        "page_number": chunk.page_number,
                        "text": chunk.text,
                        "similarity_score": round(float(score), 4)
                    })

            # Sort descending by similarity
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return results[:top_k]

        except Exception:
            # Empty vocabulary or rare edge cases fallback
            return []


# Singleton vector store instance
vector_store = VectorStore()
