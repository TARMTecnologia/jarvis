"""
Barra de Status e Indicadores de Hardware para o JARVIS.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from app.core.config import app_config
from app.core.event_bus import event_bus, EventType, Event
from app.core.state_machine import state_machine, JarvisState


class HardwareStatusBar(QWidget):
    """Exibe indicadores visuais de Microfone, Camera, Provedor de IA e Memoria."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(12)

        # 1. Provedor Ativo
        self.provider_label = QLabel(f"IA: {app_config.ai.provider.upper()} ({app_config.ai.model})")
        self.provider_label.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.provider_label)

        layout.addStretch()

        # 2. Indicador MIC
        self.mic_badge = QLabel("MIC ●")
        self.mic_badge.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.mic_badge)

        # 3. Indicador CAM
        self.cam_badge = QLabel("CAM ●")
        self.cam_badge.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.cam_badge)

        # 4. Indicador MEMORIA
        self.mem_badge = QLabel("MEMÓRIA ●")
        self.mem_badge.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.mem_badge)

        self._setup_listeners()

    def _setup_listeners(self) -> None:
        event_bus.subscribe(EventType.CAMERA_STATUS_CHANGED, self._on_camera_status)
        state_machine.add_listener(self._on_state_changed)

    def _on_camera_status(self, event: Event) -> None:
        active = event.data.get("active", False)
        if active:
            self.cam_badge.setText("CAM ● ATIVA")
            self.cam_badge.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            self.cam_badge.setText("CAM ○ PRIVACIDADE")
            self.cam_badge.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 11px;")

    def _on_state_changed(self, old_state: JarvisState, new_state: JarvisState) -> None:
        if new_state == JarvisState.OFFLINE:
            self.provider_label.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
            self.provider_label.setText(f"IA: {app_config.ai.provider.upper()} (OFFLINE)")
        else:
            self.provider_label.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 11px;")
            self.provider_label.setText(f"IA: {app_config.ai.provider.upper()} ({app_config.ai.model})")

    def refresh(self) -> None:
        self.provider_label.setText(f"IA: {app_config.ai.provider.upper()} ({app_config.ai.model})")
