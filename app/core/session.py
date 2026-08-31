"""
Gerenciamento da sessão ativa de conversação do JARVIS em memória RAM.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ConversationTurn:
    """Representa um turno de diálogo entre o usuário e o Jarvis."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # "user", "assistant", "system", "tool"
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    has_image: bool = False
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None


class ActiveSession:
    """Mantém os dados e métricas da sessão em andamento."""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini"):
        self.session_id: str = str(uuid.uuid4())
        self.provider: str = provider
        self.model: str = model
        self.start_time: float = time.time()
        self.turns: List[ConversationTurn] = []
        self.total_tokens_input: int = 0
        self.total_tokens_output: int = 0
        self.images_sent_count: int = 0
        self.audio_seconds_played: float = 0.0
        self.is_private: bool = False

    def add_turn(self, role: str, content: str, has_image: bool = False,
                 tool_calls: Optional[List[Dict[str, Any]]] = None,
                 tool_results: Optional[List[Dict[str, Any]]] = None) -> ConversationTurn:
        """Adiciona um novo turno de conversa à sessão ativa."""
        turn = ConversationTurn(
            role=role,
            content=content,
            has_image=has_image,
            tool_calls=tool_calls,
            tool_results=tool_results
        )
        self.turns.append(turn)
        if has_image:
            self.images_sent_count += 1
        return turn

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna os turnos recentes formatados para os provedores de IA."""
        recent = self.turns[-limit:] if limit > 0 else self.turns
        formatted = []
        for t in recent:
            item = {"role": t.role, "content": t.content}
            if t.tool_calls:
                item["tool_calls"] = t.tool_calls
            formatted.append(item)
        return formatted

    def reset(self, provider: Optional[str] = None, model: Optional[str] = None) -> None:
        """Reinicia a sessão com um novo ID."""
        self.session_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.turns.clear()
        if provider:
            self.provider = provider
        if model:
            self.model = model
        self.total_tokens_input = 0
        self.total_tokens_output = 0
        self.images_sent_count = 0
        self.audio_seconds_played = 0.0

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def turn_count(self) -> int:
        return len(self.turns)
