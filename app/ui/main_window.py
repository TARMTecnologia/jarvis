"""
Janela Principal da Interface Grafica HUD do JARVIS.
Integra o ORB animado, chat conversacional, visualizador de webcam, status de hardware e atalhos.
"""

import asyncio
from typing import Optional
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSplitter, QApplication, QMessageBox
)
from app.ui.styles import HUD_DARK_STYLESHEET
from app.ui.components.orb_widget import OrbWidget
from app.ui.components.audio_visualizer import AudioVisualizerWidget
from app.ui.components.status_bar import HardwareStatusBar
from app.ui.camera_widget import CameraWidget
from app.ui.conversation_widget import ConversationWidget
from app.ui.settings_window import SettingsWindow
from app.ui.memory_window import MemoryWindow
from app.ui.history_window import HistoryWindow
from app.ui.tray import JarvisTrayIcon, create_tray_icon
from app.core.orchestrator import orchestrator
from app.core.config import app_config
from app.core.event_bus import event_bus, EventType, Event
from app.core.state_machine import state_machine, JarvisState
from app.audio.audio_manager import audio_manager
from app.automation.screen_context import screen_context


class MainWindow(QMainWindow):
    """Janela principal com estetica HUD futurista."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS — Assistente Multimodal Desktop")
        self.resize(1080, 720)
        self.setMinimumSize(860, 580)
        self.setStyleSheet(HUD_DARK_STYLESHEET)
        self.setWindowIcon(create_tray_icon())

        self.tray_icon = JarvisTrayIcon(main_window=self)
        self.tray_icon.show()

        self._setup_ui()
        self._setup_event_listeners()

        # Mensagem inicial de boas-vindas
        self.conversation.add_message(
            role="assistant",
            text=f"Sistemas online. Olá, {app_config.system.user_name}! Como posso ajudá-lo hoje?"
        )

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # 1. BARRA SUPERIOR (HEADER HUD)
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #0f172a; border-radius: 8px; border: 1px solid #1e293b;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 6, 12, 6)

        title_lbl = QLabel("JARVIS HUD v1.0")
        title_lbl.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 14px; letter-spacing: 1px;")
        top_layout.addWidget(title_lbl)

        # VU Meter
        self.vu_meter = AudioVisualizerWidget()
        top_layout.addWidget(self.vu_meter)

        top_layout.addStretch()

        # Botoes de Acao Rapida
        self.btn_screen = QPushButton("Analisar Tela")
        self.btn_screen.clicked.connect(self._analyze_screen)
        top_layout.addWidget(self.btn_screen)

        self.btn_memory = QPushButton("Memória")
        self.btn_memory.clicked.connect(self.open_memory)
        top_layout.addWidget(self.btn_memory)

        self.btn_history = QPushButton("Histórico")
        self.btn_history.clicked.connect(self.open_history)
        top_layout.addWidget(self.btn_history)

        self.btn_settings = QPushButton("Configurações")
        self.btn_settings.clicked.connect(self.open_settings)
        top_layout.addWidget(self.btn_settings)

        main_layout.addWidget(top_bar)

        # 2. CONTEUDO CENTRAL (SPLITTER ESQUERDA: ORB + CAMERA | DIREITA: CHAT)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1e293b; width: 2px; }")

        # Painel Esquerdo: ORB Animado e Camera
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #080a0f; border-radius: 12px; border: 1px solid #1e293b;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)

        self.orb_widget = OrbWidget()
        left_layout.addWidget(self.orb_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.camera_widget = CameraWidget()
        left_layout.addWidget(self.camera_widget)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Painel Direito: Chat de Conversa + Campo de Entrada
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #080a0f; border-radius: 12px; border: 1px solid #1e293b;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        # Area de Mensagens
        self.conversation = ConversationWidget()
        right_layout.addWidget(self.conversation)

        # Barra de Entrada de Texto
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Digite uma mensagem ou pergunte ao Jarvis...")
        self.msg_input.returnPressed.connect(self._send_message)
        input_bar.addWidget(self.msg_input)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.setProperty("class", "primary")
        self.send_btn.clicked.connect(self._send_message)
        input_bar.addWidget(self.send_btn)

        self.mic_btn = QPushButton("Falar")
        self.mic_btn.clicked.connect(self._toggle_push_to_talk)
        input_bar.addWidget(self.mic_btn)

        right_layout.addLayout(input_bar)
        splitter.addWidget(right_panel)

        splitter.setSizes([320, 760])
        main_layout.addWidget(splitter)

        # 3. BARRA DE STATUS INFERIOR
        self.status_bar = HardwareStatusBar()
        main_layout.addWidget(self.status_bar)

    def _setup_event_listeners(self) -> None:
        """Conecta eventos do Event Bus com a interface."""
        event_bus.subscribe(EventType.AI_RESPONSE_STARTED, self._on_ai_started)
        event_bus.subscribe(EventType.AI_RESPONSE_FINISHED, self._on_ai_finished)

    def _on_ai_started(self, event: Event) -> None:
        prompt = event.data.get("prompt", "")
        # A mensagem do usuário já é adicionada no _send_message, mas para voz adicionamos aqui
        pass

    def _on_ai_finished(self, event: Event) -> None:
        text = event.data.get("text", "")
        if text:
            self.conversation.add_message(role="assistant", text=text)

    def _send_message(self) -> None:
        text = self.msg_input.text().strip()
        if not text:
            return

        self.msg_input.clear()
        self.conversation.add_message(role="user", text=text)

        # Dispara processamento assíncrono
        asyncio.run_coroutine_threadsafe(
            orchestrator.process_user_message(text, from_voice=False),
            orchestrator.get_event_loop()
        )

    def _analyze_screen(self) -> None:
        self.msg_input.setText("O que está acontecendo nessa tela?")
        self._send_message()

    def _toggle_push_to_talk(self) -> None:
        """Dispara captura imediata de fala."""
        state_machine.set_state(JarvisState.LISTENING, "Push-to-talk ativado")

    def open_settings(self) -> None:
        dlg = SettingsWindow(self)
        if dlg.exec():
            self.status_bar.refresh()
            orchestrator.reload_provider()

    def open_memory(self) -> None:
        dlg = MemoryWindow(self)
        dlg.exec()

    def open_history(self) -> None:
        dlg = HistoryWindow(self)
        dlg.exec()

    def show_and_activate(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimiza para a bandeja se configurado."""
        if app_config.system.minimize_to_tray:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "JARVIS em Segundo Plano",
                "O JARVIS continua ativo na bandeja do sistema.",
                JarvisTrayIcon.MessageIcon.Information,
                3000
            )
        else:
            self.quit_application()

    def quit_application(self) -> None:
        orchestrator.shutdown()
        self.tray_icon.hide()
        QApplication.quit()
