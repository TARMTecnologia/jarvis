"""
Memoria de Longo Prazo do JARVIS baseada em SQLite e Embeddings Locais.
"""

import json
import time
import uuid
from typing import List, Optional, Dict, Any
from app.memory.database import db
from app.memory.models import MemoryRecord, MemoryType
from app.memory.embeddings import embedding_engine
from app.core.logging_config import get_logger

logger = get_logger("memory.long_term")


class LongTermMemory:
    """Gerenciador de armazenamento permanente de memórias no SQLite."""

    def add_memory(
        self,
        text: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        importance: int = 3,
        tags: Optional[List[str]] = None,
        source: str = "conversation"
    ) -> MemoryRecord:
        """Armazena uma nova memória com seu vetor de embedding gerado localmente."""
        clean_text = text.strip()
        tags_list = tags or []
        tags_str = ",".join(tags_list)
        now = time.time()
        memory_id = str(uuid.uuid4())

        # Gera embedding vetorial local
        vec = embedding_engine.generate_embedding(clean_text)
        blob = embedding_engine.vector_to_bytes(vec)

        conn = db.get_connection()
        with conn:
            conn.execute("""
                INSERT INTO memories (
                    id, text, memory_type, importance, embedding, source, tags, created_at, last_accessed_at, access_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                memory_id,
                clean_text,
                memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type),
                importance,
                blob,
                source,
                tags_str,
                now,
                now
            ))

        logger.info(f"Nova memoria gravada: '{clean_text}' [{memory_type}]")
        return MemoryRecord(
            id=memory_id,
            text=clean_text,
            memory_type=memory_type,
            importance=importance,
            embedding=blob,
            source=source,
            tags=tags_list,
            created_at=now,
            last_accessed_at=now
        )

    def update_memory(
        self,
        memory_id: str,
        text: Optional[str] = None,
        importance: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Atualiza o conteúdo e/ou importância de uma memória existente."""
        conn = db.get_connection()
        fields = []
        params = []

        if text is not None:
            clean_text = text.strip()
            fields.append("text = ?")
            params.append(clean_text)
            
            # Recalcula embedding
            vec = embedding_engine.generate_embedding(clean_text)
            blob = embedding_engine.vector_to_bytes(vec)
            fields.append("embedding = ?")
            params.append(blob)

        if importance is not None:
            fields.append("importance = ?")
            params.append(importance)

        if tags is not None:
            fields.append("tags = ?")
            params.append(",".join(tags))

        if not fields:
            return False

        fields.append("last_accessed_at = ?")
        params.append(time.time())
        params.append(memory_id)

        query = f"UPDATE memories SET {', '.join(fields)} WHERE id = ?"
        with conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def delete_memory(self, memory_id: str) -> bool:
        """Remove uma memória específica pelo ID."""
        conn = db.get_connection()
        with conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def delete_all_memories(self) -> bool:
        """Apaga todas as memórias salvas no banco de dados."""
        conn = db.get_connection()
        with conn:
            conn.execute("DELETE FROM memories")
            logger.warning("Todas as memorias foram apagadas pelo usuario.")
            return True

    def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        """Busca uma memória pelo ID."""
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list_memories(
        self,
        search_query: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> List[MemoryRecord]:
        """Lista todas as memórias gravadas com suporte a filtro textual e tipo."""
        conn = db.get_connection()
        query = "SELECT * FROM memories WHERE 1=1 "
        params = []

        if search_query:
            query += " AND text LIKE ? "
            params.append(f"%{search_query.strip()}%")

        if memory_type and memory_type.lower() != "todos":
            query += " AND memory_type = ? "
            params.append(memory_type)

        query += " ORDER BY importance DESC, created_at DESC LIMIT ? "
        params.append(limit)

        cursor = conn.execute(query, params)
        return [self._row_to_record(row) for row in cursor.fetchall()]

    def export_memories(self, export_format: str = "json") -> str:
        """Exporta todas as memórias em formato JSON ou TXT legível."""
        memories = self.list_memories(limit=1000)
        
        if export_format.lower() == "txt":
            lines = ["=== MEMORIAS DO JARVIS ===", f"Exportado em: {time.strftime('%d/%m/%Y %H:%M:%S')}", ""]
            for m in memories:
                lines.append(f"[{m.memory_type.value.upper()}] (Importancia: {m.importance}/5) - {m.text}")
            return "\n".join(lines)

        # JSON
        data = [
            {
                "id": m.id,
                "text": m.text,
                "memory_type": m.memory_type.value,
                "importance": m.importance,
                "source": m.source,
                "tags": m.tags,
                "created_at": m.created_at
            }
            for m in memories
        ]
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _row_to_record(row: Any) -> MemoryRecord:
        tags_raw = row["tags"] or ""
        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
        return MemoryRecord(
            id=row["id"],
            text=row["text"],
            memory_type=MemoryType(row["memory_type"]) if row["memory_type"] in MemoryType._value2member_map_ else MemoryType.SEMANTIC,
            importance=row["importance"],
            embedding=row["embedding"],
            source=row["source"],
            tags=tags_list,
            created_at=row["created_at"],
            last_accessed_at=row["last_accessed_at"],
            access_count=row["access_count"]
        )


long_term_memory = LongTermMemory()
