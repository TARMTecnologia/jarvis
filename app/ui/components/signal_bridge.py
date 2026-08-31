"""
Ponte Segura de Sinais Qt (QtSignalBridge) para o JARVIS.
Recebe eventos de qualquer thread de background e os despacha com seguranca para a GUI thread do PySide6.
"""

from PySide6.QtCore import QObject, Signal
from app.core.event_bus import event_bus, EventType, Event
from app.core.state_machine import state_machine, JarvisState


class QtSignalBridge(QObject):
    """Ponte de sinais Qt thread-safe para atualizar widgets sem erros de thread."""

    # Sinais Qt (sempre executados na thread da interface)
    sig_message_received = Signal(str, str)         # (role, text)
    sig_ai_started = Signal(str)                    # (prompt)
    sig_ai_finished = Signal(str)                   # (response_text)
    sig_state_changed = Signal(str, str)            # (old_state, new_state)
    sig_audio_level = Signal(float)                 # (rms_level)
    sig_camera_status = Signal(bool)                # (is_active)
    sig_reminder_triggered = Signal(str)            # (reminder_text)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Conecta ao Event Bus e State Machine globais."""
        event_bus.subscribe(EventType.AI_RESPONSE_STARTED, self._on_ai_started)
        event_bus.subscribe(EventType.AI_RESPONSE_FINISHED, self._on_ai_finished)
        event_bus.subscribe(EventType.AUDIO_LEVEL_CHANGED, self._on_audio_level)
        event_bus.subscribe(EventType.CAMERA_STATUS_CHANGED, self._on_camera_status)
        event_bus.subscribe(EventType.REMINDER_TRIGGERED, self._on_reminder_triggered)
        state_machine.add_listener(self._on_state_changed)

    def _on_ai_started(self, event: Event) -> None:
        prompt = event.data.get("prompt", "")
        self.sig_ai_started.emit(prompt)

    def _on_ai_finished(self, event: Event) -> None:
        text = event.data.get("text", "")
        if text:
            self.sig_ai_finished.emit(text)
            self.sig_message_received.emit("assistant", text)

    def _on_audio_level(self, event: Event) -> None:
        rms = event.data.get("rms", 0.0)
        self.sig_audio_level.emit(rms)

    def _on_camera_status(self, event: Event) -> None:
        active = event.data.get("active", False)
        self.sig_camera_status.emit(active)

    def _on_reminder_triggered(self, event: Event) -> None:
        text = event.data.get("text", "")
        self.sig_reminder_triggered.emit(text)

    def _on_state_changed(self, old_state: JarvisState, new_state: JarvisState) -> None:
        self.sig_state_changed.emit(old_state.value, new_state.value)

    def emit_user_message(self, text: str) -> None:
        """Envia mensagem digitada pelo usuario para a UI."""
        self.sig_message_received.emit("user", text)


signal_bridge = QtSignalBridge()
