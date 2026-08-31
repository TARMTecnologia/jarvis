"""
Memoria de Curto Prazo (RAM) do JARVIS.
Mantem a janela de contexto recente da conversa ativa.
"""

from typing import List, Dict, Any, Optional
from app.memory.models import MessageRecord
import time


class ShortTermMemory:
    """Buffer de mensagens recentes em memoria RAM."""

    def __init__(self, max_turns: int = 12):
        self.max_turns = max_turns
        self._turns: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, has_image: bool = False, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """Adiciona uma nova mensagem a memoria de curto prazo."""
        entry = {
            "role": role,
            "content": content,
            "has_image": has_image,
            "tool_calls": tool_calls,
            "timestamp": time.time()
        }
        self._turns.append(entry)
        
        # Mantem o tamanho da janela de turnos dentro do limite configurado
        if len(self._turns) > self.max_turns * 2:
            self._turns = self._turns[-self.max_turns * 2:]

    def get_context_messages(self) -> List[Dict[str, Any]]:
        """Retorna as mensagens formatadas para envio ao provedor de IA."""
        return [
            {
                "role": t["role"],
                "content": t["content"],
                **({"tool_calls": t["tool_calls"]} if t.get("tool_calls") else {})
            }
            for t in self._turns
        ]

    def clear(self) -> None:
        """Limpa a memoria de curto prazo."""
        self._turns.clear()

    @property
    def turn_count(self) -> int:
        return len(self._turns)
