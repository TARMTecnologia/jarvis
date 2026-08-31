"""
Gerenciador Central de Memoria do JARVIS.
Coordena memoria de curto prazo, longo prazo, recuperacao semantica e comandos de usuario.
"""

import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import long_term_memory, LongTermMemory
from app.memory.retrieval import semantic_retrieval, SemanticRetrievalEngine
from app.memory.summarizer import memory_summarizer, MemorySummarizer
from app.memory.database import db
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("memory.manager")


class MemoryManager:
    """Interface unificada de memoria para o JARVIS."""

    def __init__(self):
        self.short_term = ShortTermMemory(max_turns=app_config.memory.consolidation_turn_interval)
        self.long_term: LongTermMemory = long_term_memory
        self.retrieval: SemanticRetrievalEngine = semantic_retrieval
        self.summarizer: MemorySummarizer = memory_summarizer

    def handle_explicit_commands(self, user_text: str) -> Optional[str]:
        """Verifica e executa comandos explicitos de lembranca ou esquecimento."""
        result = self.summarizer.process_explicit_memory_command(user_text)
        if result:
            _, reply_message = result
            return reply_message
        return None

    def record_turn(
        self,
        conversation_id: str,
        role: str,
        content: str,
        has_image: bool = False,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Salva a mensagem na memoria de curto prazo e no banco SQLite permanente (se nao estiver em modo privado)."""
        self.short_term.add_message(role=role, content=content, has_image=has_image, tool_calls=tool_calls)

        if app_config.memory.private_mode:
            return  # Modo privado nao grava em disco

        try:
            conn = db.get_connection()
            with conn:
                # Garante que a conversa existe
                conn.execute("""
                    INSERT OR IGNORE INTO conversations (id, title, provider, model, created_at, updated_at, message_count)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (
                    conversation_id,
                    "Conversa " + time.strftime("%d/%m %H:%M"),
                    app_config.ai.provider,
                    app_config.ai.model,
                    time.time(),
                    time.time()
                ))

                # Grava a mensagem
                msg_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO messages (id, conversation_id, role, content, has_image, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (msg_id, conversation_id, role, content, 1 if has_image else 0, time.time()))

                # Atualiza contagem
                conn.execute("""
                    UPDATE conversations
                    SET updated_at = ?, message_count = message_count + 1
                    WHERE id = ?
                """, (time.time(), conversation_id))
        except Exception as e:
            logger.error(f"Erro ao persistir mensagem no SQLite: {e}")

    def prepare_augmented_system_prompt(self, base_system_prompt: str, user_query: str) -> str:
        """Enriquece o System Prompt com as memorias relevantes encontradas por busca semantica."""
        if not app_config.memory.enabled or app_config.memory.private_mode:
            return base_system_prompt

        max_k = getattr(app_config.memory, "max_retrieval_count", getattr(app_config.memory, "max_retrieval_results", 5))
        retrieved_context = self.retrieval.format_context_for_prompt(
            query=user_query,
            top_k=max_k,
            threshold=app_config.memory.similarity_threshold
        )

        if retrieved_context:
            return f"{base_system_prompt}\n\n{retrieved_context}"
        return base_system_prompt


memory_manager = MemoryManager()
