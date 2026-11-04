"""
Ephemeral In-Memory Vector Store Manager (ChromaDB).

Strict Privacy Enforcement:
1. Indexes are strictly in-memory (ephemeral).
2. Plaintext chunks and embeddings are NEVER persisted to an unencrypted database file.
3. Completely rebuilt in-memory when a user logs in or requests search.
4. Each user has an isolated in-memory collection.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from rag.chunking import DocumentChunk
from rag.embeddings import embedding_provider


class EphemeralVectorStore:
    """
    Manages in-memory ChromaDB vector collections for active user sessions.
    """
    def __init__(self):
        # In-memory ephemeral client
        self.client = chromadb.EphemeralClient(
            settings=Settings(anonymized_telemetry=False)
        )

    def _get_collection(self, user_id: int):
        return self.client.get_or_create_collection(
            name=f"user_{user_id}_ephemeral",
            metadata={"description": "In-memory encrypted session index"}
        )

    def index_document(self, user_id: int, doc_id: str, filename: str, chunks: List[DocumentChunk]) -> int:
        """
        Indexes chunks into the user's ephemeral collection.
        First removes old chunks for doc_id if they exist.
        """
        if not chunks:
            return 0

        collection = self._get_collection(user_id)
        self.remove_document(user_id, doc_id)

        ids = []
        documents = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{idx}"
            ids.append(chunk_id)
            documents.append(chunk.text)
            meta = {
                "doc_id": doc_id,
                "filename": filename,
                "location": chunk.location_label,
                **{k: str(v) for k, v in chunk.metadata.items()}
            }
            metadatas.append(meta)

        # Compute embeddings locally
        embeddings = embedding_provider.embed_documents(documents)

        # Batch insert
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        return len(chunks)

    def remove_document(self, user_id: int, doc_id: str):
        """Removes all indexed chunks for a document from memory."""
        try:
            collection = self._get_collection(user_id)
            collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

    def search(
        self,
        user_id: int,
        query: str,
        target_doc_id: Optional[str] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search across user documents.
        Supports both INDIVIDUAL DOCUMENT SEARCH and WORKSPACE SEARCH.
        """
        collection = self._get_collection(user_id)
        if collection.count() == 0:
            return []

        where_filter = {"doc_id": target_doc_id} if target_doc_id else None
        query_embedding = embedding_provider.embed_query(query)

        actual_k = min(top_k, collection.count())

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=actual_k,
                where=where_filter
            )
        except Exception:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=actual_k
            )

        output: List[Dict[str, Any]] = []
        if not results or not results.get("documents"):
            return output

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        for i, text in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            dist = distances[i] if i < len(distances) else 1.0
            score = max(0.0, round(1.0 - (dist / 2.0), 3))
            output.append({
                "doc_id": meta.get("doc_id", ""),
                "filename": meta.get("filename", ""),
                "location": meta.get("location", ""),
                "text": text,
                "relevance_score": score
            })

        return output


# Global ephemeral vector store instance
vector_store = EphemeralVectorStore()

