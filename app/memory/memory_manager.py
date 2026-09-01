"""
Gerenciador Central de Memoria do JARVIS.
Coordena memoria de curto prazo, longo prazo solida, recuperacao semantica e perfil permanente do mentor.
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
    """Interface unificada de memoria solida e semantica para o JARVIS."""

    def __init__(self):
        self.short_term = ShortTermMemory(max_turns=app_config.memory.consolidation_turn_interval)
        self.long_term: LongTermMemory = long_term_memory
        self.retrieval: SemanticRetrievalEngine = semantic_retrieval
        self.summarizer: MemorySummarizer = memory_summarizer

    def handle_explicit_commands(self, user_text: str) -> Optional[str]:
        """Verifica e executa comandos explicitos de lembranca, cadastro de nome ou esquecimento."""
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
            return

        try:
            conn = db.get_connection()
            with conn:
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

                msg_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO messages (id, conversation_id, role, content, has_image, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (msg_id, conversation_id, role, content, 1 if has_image else 0, time.time()))

                conn.execute("""
                    UPDATE conversations
                    SET updated_at = ?, message_count = message_count + 1
                    WHERE id = ?
                """, (time.time(), conversation_id))
        except Exception as e:
            logger.error(f"Erro ao persistir mensagem no SQLite: {e}")

    def get_mentor_core_profile(self) -> str:
        """Retorna o bloco de memoria solida do mentor fixado no topo do contexto."""
        user_name = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Senhor"
        
        # Recupera fatos com alta importancia (fatos, preferencias e projetos permanentes)
        core_memories = self.long_term.list_memories(limit=8)
        facts = [f"- {m.text}" for m in core_memories if m.importance >= 4]

        profile_lines = [
            "### [MEMÓRIA SÓLIDA DO MENTOR]",
            f"- Nome Oficial do Mentor: {user_name}"
        ]
        if facts:
            profile_lines.append("- Fatos e Preferências Fixadas:")
            profile_lines.extend(facts[:6])

        return "\n".join(profile_lines)

    def prepare_augmented_system_prompt(self, base_system_prompt: str, user_query: str) -> str:
        """Enriquece o System Prompt com a Memoria Solida do Mentor e busca semantica."""
        if not app_config.memory.enabled or app_config.memory.private_mode:
            return base_system_prompt

        core_profile = self.get_mentor_core_profile()

        max_k = getattr(app_config.memory, "max_retrieval_count", getattr(app_config.memory, "max_retrieval_results", 5))
        retrieved_context = self.retrieval.format_context_for_prompt(
            query=user_query,
            top_k=max_k,
            threshold=app_config.memory.similarity_threshold
        )

        augmented = f"{base_system_prompt}\n\n{core_profile}"
        if retrieved_context:
            augmented = f"{augmented}\n\n{retrieved_context}"
            
        return augmented


memory_manager = MemoryManager()
