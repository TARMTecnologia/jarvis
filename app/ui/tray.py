"""
Icone e Menu de Contexto da Bandeja do Sistema (System Tray) para o JARVIS.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget
from app.core.config import app_config
from app.audio.audio_manager import audio_manager
from app.vision.vision_manager import vision_manager
from app.platform.windows import windows_platform


def create_tray_icon() -> QIcon:
    """Cria um icone procedural brilhante para a bandeja."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor(0, 210, 255))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, 24, 24)

    painter.setBrush(QColor(255, 255, 255))
    painter.drawEllipse(10, 10, 12, 12)
    painter.end()
    return QIcon(pix)


class JarvisTrayIcon(QSystemTrayIcon):
    """Gerenciador do icone da bandeja do sistema."""

    def __init__(self, main_window: QWidget, parent: QWidget = None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self.setIcon(create_tray_icon())
        self.setToolTip("JARVIS — Assistente Multimodal Desktop")

        # Conecta notificacoes nativas ao balao da tray
        windows_platform.set_tray_callback(self.show_tray_message)

        self._create_menu()
        self.activated.connect(self._on_tray_activated)

    def _create_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                border: 1px solid #00d2ff;
                color: #f8fafc;
                padding: 6px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
            }
        """)

        # Abrir
        open_action = menu.addAction("Abrir JARVIS")
        open_action.triggered.connect(self.main_window.show_and_activate)

        menu.addSeparator()

        # Toggle Mic
        self.mic_action = menu.addAction("Microfone Ativo")
        self.mic_action.setCheckable(True)
        self.mic_action.setChecked(audio_manager.microphone.is_recording)
        self.mic_action.triggered.connect(self._toggle_mic)

        # Toggle Camera
        self.cam_action = menu.addAction("Câmera Ativa")
        self.cam_action.setCheckable(True)
        self.cam_action.setChecked(vision_manager.is_active)
        self.cam_action.triggered.connect(self._toggle_camera)

        # Modo Silencioso
        self.silent_action = menu.addAction("Modo Silencioso")
        self.silent_action.setCheckable(True)
        self.silent_action.setChecked(app_config.system.silent_mode)
        self.silent_action.triggered.connect(self._toggle_silent)

        menu.addSeparator()

        # Janelas
        settings_action = menu.addAction("Configurações...")
        settings_action.triggered.connect(self.main_window.open_settings)

        memory_action = menu.addAction("Gerenciador de Memória...")
        memory_action.triggered.connect(self.main_window.open_memory)

        menu.addSeparator()

        # Sair
        quit_action = menu.addAction("Encerrar JARVIS")
        quit_action.triggered.connect(self.main_window.quit_application)

        self.setContextMenu(menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.main_window.show_and_activate()

    def _toggle_mic(self) -> None:
        if audio_manager.microphone.is_recording:
            audio_manager.microphone.stop()
            self.mic_action.setChecked(False)
        else:
            audio_manager.microphone.start()
            self.mic_action.setChecked(True)

    def _toggle_camera(self) -> None:
        active = vision_manager.toggle_camera()
        self.cam_action.setChecked(active)

    def _toggle_silent(self) -> None:
        app_config.system.silent_mode = not app_config.system.silent_mode
        app_config.save()
        self.silent_action.setChecked(app_config.system.silent_mode)

    def show_tray_message(self, title: str, message: str) -> None:
        self.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )
