"""
Vector Database Store Module.

Supports:
1. Cloud Mode (Supabase pgvector):
   - Chunks stored in public.document_chunks with vector(384).
   - Chunk text and metadata encrypted with AES-256-GCM at rest.
   - Vector similarity search executed via match_document_chunks RPC function,
     strictly filtered by auth.uid() using user's JWT.

2. Local Mode (ChromaDB EphemeralVectorStore):
   - Ephemeral in-memory vector store isolated per user workspace.
"""

from typing import List, Dict, Any, Optional
import uuid
import chromadb
from chromadb.config import Settings
from config import IS_CLOUD_MODE
from rag.chunking import DocumentChunk
from rag.embeddings import embedding_provider
from database.cloud_db import get_user_supabase_client
from auth.cloud_encryption import encrypt_text, decrypt_text


# =====================================================================
# 1. Cloud Mode: Supabase pgvector Integration
# =====================================================================

class CloudVectorStore:
    def __init__(self, user_id: str, jwt_token: str):
        self.user_id = str(user_id)
        self.jwt_token = jwt_token
        self.client = get_user_supabase_client(jwt_token)

    def add_chunks(self, doc_id: str, version_number: int, chunks: List[Dict[str, Any]]) -> bool:
        """
        Computes embeddings, encrypts text at rest, and inserts records into document_chunks.
        """
        if not self.client or not chunks:
            return False

        try:
            self.client.table("document_chunks").delete().eq("document_id", doc_id).eq("version_number", version_number).execute()

            texts = [c.text if hasattr(c, "text") else c["text"] for c in chunks]
            embeddings = embedding_provider.embed_documents(texts)

            import json
            records = []
            for idx, chunk in enumerate(chunks):
                text_val = chunk.text if hasattr(chunk, "text") else chunk["text"]
                meta_val = chunk.metadata if hasattr(chunk, "metadata") else chunk.get("metadata", {})
                meta_json = json.dumps(meta_val) if isinstance(meta_val, dict) else str(meta_val)
                record = {
                    "user_id": self.user_id,
                    "document_id": doc_id,
                    "version_number": version_number,
                    "chunk_index": idx,
                    "chunk_ciphertext": encrypt_text(text_val, self.user_id),
                    "source_metadata_ciphertext": encrypt_text(meta_json, self.user_id),
                    "embedding": embeddings[idx]
                }
                records.append(record)

            self.client.table("document_chunks").insert(records).execute()
            return True
        except Exception as e:
            print(f"[PGVECTOR] add_chunks error: {e}")
            return False

    def search(self, query: str, top_k: int = 5, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes semantic vector search via match_document_chunks RPC function.
        Decrypts matched chunk text in memory before returning.
        """
        if not self.client:
            return []

        try:
            query_embedding = embedding_provider.embed_query(query)
            params = {
                "query_embedding": query_embedding,
                "match_threshold": 0.05,
                "match_count": top_k,
                "filter_doc_id": doc_id
            }

            resp = self.client.rpc("match_document_chunks", params).execute()
            results = []
            for r in (resp.data or []):
                decrypted_text = decrypt_text(r["chunk_ciphertext"], self.user_id)
                raw_meta = decrypt_text(r.get("source_metadata_ciphertext") or "", self.user_id)
                meta_dict = {}
                try:
                    meta_dict = json.loads(raw_meta) if raw_meta and raw_meta.startswith("{") else {"raw": raw_meta}
                except Exception:
                    meta_dict = {"raw": raw_meta}

                results.append({
                    "id": r["id"],
                    "document_id": r["document_id"],
                    "version_number": r["version_number"],
                    "chunk_index": r["chunk_index"],
                    "text": decrypted_text,
                    "metadata": meta_dict,
                    "similarity": r.get("similarity", 0.0)
                })
            return results
        except Exception as e:
            print(f"[PGVECTOR] search error: {e}")
            return []


# =====================================================================
# 2. Local Mode: ChromaDB Ephemeral Vector Store
# =====================================================================

class EphemeralVectorStore:
    def __init__(self):
        self.client = chromadb.EphemeralClient(
            settings=Settings(anonymized_telemetry=False)
        )

    def _get_collection(self, user_id: int):
        return self.client.get_or_create_collection(
            name=f"user_{user_id}_ephemeral",
            metadata={"description": "In-memory encrypted session index"}
        )

    def index_document(self, user_id: int, doc_id: str, filename: str, chunks: List[DocumentChunk]) -> int:
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

        embeddings = embedding_provider.embed_documents(documents)

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        return len(chunks)

    def remove_document(self, user_id: int, doc_id: str):
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


# Global local vector store instance
vector_store = EphemeralVectorStore()


# =====================================================================
# Factory Function
# =====================================================================

def get_vector_store(session_state: Any):
    """Instantiates CloudVectorStore in cloud mode or EphemeralVectorStore in local mode."""
    if IS_CLOUD_MODE:
        user_id = session_state.get("user_id")
        jwt_token = session_state.get("jwt_token", "")
        return CloudVectorStore(user_id=user_id, jwt_token=jwt_token)
    else:
        return vector_store
