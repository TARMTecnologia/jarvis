"""
Gerador de Embeddings Semanticos Locais para o JARVIS.
Utiliza Sentence-Transformers localmente com fallback resiliente TF-IDF caso o modelo esteja indisponivel.
"""

import math
import re
import numpy as np
from typing import List, Optional
from app.core.logging_config import get_logger

logger = get_logger("memory.embeddings")


class LocalEmbeddingEngine:
    """Motor de embeddings vetoriais com fallback offline instantaneo."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384
        self._use_fallback = False
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Tenta carregar o modelo SentenceTransformers em background ou ativa fallback."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            if hasattr(self._model, "get_embedding_dimension"):
                self._dimension = self._model.get_embedding_dimension()
            elif hasattr(self._model, "get_sentence_embedding_dimension"):
                self._dimension = self._model.get_sentence_embedding_dimension()
            else:
                self._dimension = 384
            logger.info(f"Modelo de Embeddings '{self.model_name}' carregado com sucesso (dimensao {self._dimension}).")
        except Exception as e:
            logger.warning(f"SentenceTransformers nao inicializado ({e}). Ativando fallback de vetorizacao local.")
            self._use_fallback = True
            self._dimension = 256

    def generate_embedding(self, text: str) -> np.ndarray:
        """Gera vetor normalizado de embedding para o texto fornecido."""
        if not text or not text.strip():
            return np.zeros(self._dimension, dtype=np.float32)

        if not self._use_fallback and self._model is not None:
            try:
                emb = self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return emb.astype(np.float32)
            except Exception as e:
                logger.error(f"Erro ao inferir embedding via modelo: {e}")

        # Fallback local deterministico baseado em hashing TF-IDF
        return self._generate_fallback_embedding(text)

    def _generate_fallback_embedding(self, text: str) -> np.ndarray:
        """Gera um vetor pseudo-semantico baseado em hashing de n-gramas e frequencia de palavras."""
        words = re.findall(r"\w+", text.lower())
        vec = np.zeros(self._dimension, dtype=np.float32)

        if not words:
            return vec

        for word in words:
            h = hash(word) % self._dimension
            vec[h] += 1.0

            for i in range(len(word) - 2):
                tri = word[i:i+3]
                h_tri = hash(tri) % self._dimension
                vec[h_tri] += 0.5

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    @staticmethod
    def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Calcula a similaridade de cosseno entre dois vetores normalizados."""
        if vec_a is None or vec_b is None or len(vec_a) == 0 or len(vec_b) == 0:
            return 0.0
        dot_product = float(np.dot(vec_a, vec_b))
        return max(0.0, min(1.0, dot_product))

    @staticmethod
    def vector_to_bytes(vec: np.ndarray) -> bytes:
        """Serializa o vetor numpy para bytes binarios para salvar no SQLite BLOB."""
        return vec.astype(np.float32).tobytes()

    @staticmethod
    def bytes_to_vector(blob: bytes) -> np.ndarray:
        """Deserializa bytes binarios do SQLite para array numpy."""
        if not blob:
            return np.array([], dtype=np.float32)
        return np.frombuffer(blob, dtype=np.float32)


embedding_engine = LocalEmbeddingEngine()
