"""
Barramento de eventos assíncrono para desacoplamento entre UI, Áudio, Visão, IA e Ferramentas.
Permite publicação e subscrição de eventos com suporte a funções síncronas e assíncronas.
"""

import asyncio
import inspect
from enum import Enum
from typing import Callable, Dict, List, Any, Optional
from app.core.logging_config import get_logger

logger = get_logger("core.event_bus")


class EventType(str, Enum):
    """Tipos de eventos trafegados no sistema JARVIS."""
    # Voz e Áudio
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    USER_SPEECH_STARTED = "USER_SPEECH_STARTED"
    USER_SPEECH_FINISHED = "USER_SPEECH_FINISHED"
    USER_TRANSCRIPTION_RECEIVED = "USER_TRANSCRIPTION_RECEIVED"
    AUDIO_LEVEL_CHANGED = "AUDIO_LEVEL_CHANGED"
    SPEAKER_STARTED = "SPEAKER_STARTED"
    SPEAKER_FINISHED = "SPEAKER_FINISHED"
    SPEAKER_INTERRUPTED = "SPEAKER_INTERRUPTED"

    # IA e Resposta
    AI_RESPONSE_STARTED = "AI_RESPONSE_STARTED"
    AI_RESPONSE_CHUNK = "AI_RESPONSE_CHUNK"
    AI_RESPONSE_FINISHED = "AI_RESPONSE_FINISHED"
    AI_AUDIO_CHUNK = "AI_AUDIO_CHUNK"

    # Visão e Câmera
    CAMERA_FRAME_RECEIVED = "CAMERA_FRAME_RECEIVED"
    SCENE_CHANGED = "SCENE_CHANGED"
    CAMERA_STATUS_CHANGED = "CAMERA_STATUS_CHANGED"

    # Ferramentas e Automação
    TOOL_REQUESTED = "TOOL_REQUESTED"
    TOOL_CONFIRMATION_REQUIRED = "TOOL_CONFIRMATION_REQUIRED"
    TOOL_CONFIRMED = "TOOL_CONFIRMED"
    TOOL_CANCELLED = "TOOL_CANCELLED"
    TOOL_FINISHED = "TOOL_FINISHED"

    # Memória e Lembretes
    MEMORY_STORED = "MEMORY_STORED"
    MEMORY_DELETED = "MEMORY_DELETED"
    REMINDER_TRIGGERED = "REMINDER_TRIGGERED"

    # Estado e Sistema
    STATE_CHANGED = "STATE_CHANGED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    NOTIFICATION_REQUESTED = "NOTIFICATION_REQUESTED"


class Event:
    """Estrutura padrão de uma mensagem de evento."""
    def __init__(self, event_type: EventType, data: Optional[Dict[str, Any]] = None, source: str = "system"):
        self.type = event_type
        self.data = data or {}
        self.source = source

    def __repr__(self):
        return f"<Event {self.type.value} from {self.source}>"


class EventBus:
    """Barramento central de publicação e subscrição de eventos."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Event], Any]]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        """Registra um manipulador para um tipo de evento específico."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        """Remove um manipulador registrado."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(self, event_type: EventType, data: Optional[Dict[str, Any]] = None, source: str = "system") -> None:
        """Publica um evento para todos os ouvintes inscritos de forma segura."""
        event = Event(event_type, data, source)
        handlers = self._subscribers.get(event_type, [])

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    try:
                        loop = self._loop or asyncio.get_running_loop()
                        asyncio.run_coroutine_threadsafe(handler(event), loop)
                    except RuntimeError:
                        # Se não houver loop ativo nesta thread, criar task se possível
                        pass
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Erro ao processar evento {event_type.value} no handler {handler}: {e}")

    async def publish_async(self, event_type: EventType, data: Optional[Dict[str, Any]] = None, source: str = "system") -> None:
        """Publica um evento aguardando os handlers assíncronos."""
        event = Event(event_type, data, source)
        handlers = self._subscribers.get(event_type, [])

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Erro ao processar evento assíncrono {event_type.value}: {e}")


# Instância global compartilhada
event_bus = EventBus()
