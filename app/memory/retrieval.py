"""
Motor de Recuperacao Semantica de Memorias para o JARVIS.
Busca vetorial por similaridade de cosseno com ranking ponderado por relevancia.
"""

import time
from typing import List, Tuple, Optional
import numpy as np
from app.memory.database import db
from app.memory.models import MemoryRecord, MemoryType
from app.memory.embeddings import embedding_engine
from app.core.logging_config import get_logger

logger = get_logger("memory.retrieval")


class SemanticRetrievalEngine:
    """Recupera memorias mais relevantes para enriquecer o contexto da IA."""

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.35
    ) -> List[Tuple[MemoryRecord, float]]:
        """
        Retorna as memorias mais semelhantes a pergunta do usuario com suas pontuacoes.
        """
        if not query or not query.strip():
            return []

        query_vec = embedding_engine.generate_embedding(query.strip())
        conn = db.get_connection()
        cursor = conn.execute("SELECT * FROM memories")
        rows = cursor.fetchall()

        if not rows:
            return []

        scored_memories: List[Tuple[MemoryRecord, float]] = []
        now = time.time()
        accessed_ids = []

        for row in rows:
            blob = row["embedding"]
            if not blob:
                continue

            mem_vec = embedding_engine.bytes_to_vector(blob)
            sim = embedding_engine.cosine_similarity(query_vec, mem_vec)

            # Ponderacao: da um pequeno bonus para memorias com importancia mais alta (1 a 5)
            importance_boost = (row["importance"] - 3) * 0.05
            final_score = sim + importance_boost

            if final_score >= similarity_threshold:
                tags_raw = row["tags"] or ""
                tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
                record = MemoryRecord(
                    id=row["id"],
                    text=row["text"],
                    memory_type=MemoryType(row["memory_type"]) if row["memory_type"] in MemoryType._value2member_map_ else MemoryType.SEMANTIC,
                    importance=row["importance"],
                    embedding=blob,
                    source=row["source"],
                    tags=tags_list,
                    created_at=row["created_at"],
                    last_accessed_at=row["last_accessed_at"],
                    access_count=row["access_count"]
                )
                scored_memories.append((record, final_score))

        # Ordena decrescente pela pontuacao final
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        top_results = scored_memories[:top_k]

        # Atualiza contadores de acesso no banco
        if top_results:
            accessed_ids = [m.id for m, _ in top_results]
            with conn:
                for mid in accessed_ids:
                    conn.execute(
                        "UPDATE memories SET last_accessed_at = ?, access_count = access_count + 1 WHERE id = ?",
                        (now, mid)
                    )

        logger.debug(f"Recuperadas {len(top_results)} memorias relevantes para a query: '{query[:30]}...'")
        return top_results

    def format_context_for_prompt(self, query: str, top_k: int = 5, threshold: float = 0.35) -> str:
        """Formata as memorias relevantes em texto pronto para injecao no System Prompt."""
        results = self.retrieve(query, top_k=top_k, similarity_threshold=threshold)
        if not results:
            return ""

        lines = ["\n[MEMORIAS RELEVANTES SOBRE O USUARIO E CONTEXTO]:"]
        for mem, score in results:
            lines.append(f"- {mem.text} (tipo: {mem.memory_type.value})")
        lines.append("[FIM DAS MEMORIAS - Utilize essas informacoes naturalmente]\n")

        return "\n".join(lines)


semantic_retrieval = SemanticRetrievalEngine()
