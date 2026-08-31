"""
Máquina de Estados do JARVIS.
Gerencia os estados do assistente e notifica observadores (como o Orb visual e a UI).
"""

from enum import Enum
from typing import Callable, List, Dict, Any
from app.core.logging_config import get_logger

logger = get_logger("core.state_machine")


class JarvisState(str, Enum):
    """Estados operacionais do assistente JARVIS."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    EXECUTING_TOOL = "EXECUTING_TOOL"
    WATCHING = "WATCHING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class StateMachine:
    """Controlador de transição de estados com callbacks."""

    def __init__(self, initial_state: JarvisState = JarvisState.IDLE):
        self._current_state = initial_state
        self._previous_state = initial_state
        self._listeners: List[Callable[[JarvisState, JarvisState], None]] = []

    @property
    def current_state(self) -> JarvisState:
        return self._current_state

    @property
    def previous_state(self) -> JarvisState:
        return self._previous_state

    def set_state(self, new_state: JarvisState, reason: str = "") -> None:
        """Transiciona para um novo estado e notifica os listeners."""
        if new_state == self._current_state:
            return

        old_state = self._current_state
        self._previous_state = old_state
        self._current_state = new_state

        logger.debug(f"Estado alterado: {old_state.value} -> {new_state.value} ({reason})")

        for listener in self._listeners:
            try:
                listener(old_state, new_state)
            except Exception as e:
                logger.error(f"Erro ao executar listener de estado: {e}")

    def add_listener(self, callback: Callable[[JarvisState, JarvisState], None]) -> None:
        """Registra um callback a ser chamado em cada transição de estado."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[JarvisState, JarvisState], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)


# Instância global compartilhada
state_machine = StateMachine()
