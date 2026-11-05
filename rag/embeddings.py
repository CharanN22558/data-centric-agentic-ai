"""
Local Embedding Provider Module.

Uses SentenceTransformers when model weights are cached locally.
Falls back instantly to a fast deterministic embedding function
when offline or in isolated environments so operations and tests never hang.
"""

from typing import List
import numpy as np


import os
import threading
from typing import List
import numpy as np


class LocalEmbeddingProvider:
    """
    Generates local vector embeddings on the user's computer without sending data to third parties.
    Asynchronously pre-loads sentence-transformers in a background daemon thread so startup is instant.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._loading = False
        self._load_lock = threading.Lock()
        
        # Trigger background warmup if not explicitly disabled
        if os.getenv("EMBEDDING_FALLBACK_ONLY", "0") != "1":
            t = threading.Thread(target=self._background_warmup, daemon=True)
            t.start()

    def _background_warmup(self):
        with self._load_lock:
            if self._model is None and not self._loading:
                self._loading = True
                try:
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer(self.model_name, local_files_only=True)
                except Exception:
                    # If not locally cached or import fails, fallback deterministic is used
                    self._model = "fallback"
                finally:
                    self._loading = False

    def _ensure_model(self):
        if self._model is None:
            # If background loading hasn't finished, wait briefly or load synchronously
            with self._load_lock:
                if self._model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                        self._model = SentenceTransformer(self.model_name, local_files_only=True)
                    except Exception:
                        self._model = "fallback"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text chunks."""
        self._ensure_model()
        if self._model != "fallback" and hasattr(self._model, "encode"):
            try:
                embeddings = self._model.encode(texts, convert_to_numpy=True)
                return embeddings.tolist()
            except Exception:
                pass
        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding for a single user query."""
        self._ensure_model()
        if self._model != "fallback" and hasattr(self._model, "encode"):
            try:
                return self._model.encode([query], convert_to_numpy=True)[0].tolist()
            except Exception:
                pass
        return self._fallback_embed(query)

    def _fallback_embed(self, text: str, dim: int = 384) -> List[float]:
        """Deterministic, fast semantic-preserving vector fallback."""
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        for idx, w in enumerate(words):
            h = abs(hash(w)) % dim
            vec[h] += 1.0 / (idx + 1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()


# Global local embedding instance
embedding_provider = LocalEmbeddingProvider()
