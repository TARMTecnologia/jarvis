"""
Janela Principal da Interface HUD do JARVIS.
Incorpora o Rosto Robótico Low-Poly Futurista animado, Chat em Tempo Real, Camera, VU Meter e Acoes Rapidas.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSplitter, QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

from app.core.config import app_config
from app.core.state_machine import state_machine, JarvisState
from app.core.event_bus import event_bus, EventType
from app.ui.components.face_widget import LowPolyFaceWidget
from app.ui.camera_widget import CameraWidget
from app.ui.conversation_widget import ConversationWidget
from app.ui.components.audio_visualizer import AudioVisualizerWidget
from app.ui.components.signal_bridge import signal_bridge
from app.ui.memory_window import MemoryWindow
from app.ui.history_window import HistoryWindow
from app.ui.settings_window import SettingsWindow
from app.automation.screen_context import screen_context
from app.ui.styles import HUD_DARK_STYLESHEET
from app.core.logging_config import get_logger

logger = get_logger("ui.main")


class MainWindow(QMainWindow):
    """Janela Principal com visual futurista e Rosto Holográfico Low-Poly."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS — Assistente de Inteligência Artificial")
        self.resize(1060, 680)
        self.setStyleSheet(HUD_DARK_STYLESHEET)

        self._setup_ui()
        self._setup_signals()

        # Mensagem inicial de boas-vindas
        effective_name = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Senhor"
        self.conversation.add_message(
            role="assistant",
            text=f"Sistemas operacionais. Olá, {effective_name}! Em que posso ser útil hoje?"
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

        title_lbl = QLabel("JARVIS HUD AI")
        title_lbl.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 15px; letter-spacing: 1.5px;")
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

        # 2. CONTEUDO CENTRAL (SPLITTER ESQUERDA: ROSTO ROBÔ + CÂMERA | DIREITA: CHAT)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1e293b; width: 2px; }")

        # Painel Esquerdo: Rosto Robótico Low-Poly & Câmera
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #080a0f; border-radius: 12px; border: 1px solid #1e293b;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        # Abas Visuais: Rosto Robótico ou Preview da Câmera
        self.visual_tabs = QTabWidget()
        
        # Tab 1: Rosto Robótico Low-Poly
        self.face_widget = LowPolyFaceWidget(use_amber=True)
        self.visual_tabs.addTab(self.face_widget, "🤖 Avatar Robô")

        # Tab 2: Câmera
        self.camera_widget = CameraWidget()
        self.visual_tabs.addTab(self.camera_widget, "📷 Câmera")

        left_layout.addWidget(self.visual_tabs)
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

        right_layout.addLayout(input_bar)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter)

        # 3. BARRA INFERIOR (STATUS BAR HUD)
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("background-color: #0f172a; border-radius: 6px; border: 1px solid #1e293b;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12, 4, 12, 4)

        self.status_lbl = QLabel("● Sistema Pronto")
        self.status_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: bold;")
        bottom_layout.addWidget(self.status_lbl)

        bottom_layout.addStretch()

        self.provider_lbl = QLabel(f"IA: {app_config.ai.provider.upper()} ({app_config.ai.model})")
        self.provider_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        bottom_layout.addWidget(self.provider_lbl)

        main_layout.addWidget(bottom_bar)

    def _setup_signals(self) -> None:
        signal_bridge.user_message_received.connect(self._on_user_message_received)
        signal_bridge.ai_response_received.connect(self._on_ai_response_received)
        state_machine.add_callback(self._on_state_changed)

    def _send_message(self) -> None:
        text = self.msg_input.text().strip()
        if not text:
            return

        self.conversation.add_message(role="user", text=text)
        self.msg_input.clear()
        self.msg_input.setEnabled(False)
        self.send_btn.setEnabled(False)

        import asyncio
        from app.core.orchestrator import orchestrator

        if orchestrator._loop and orchestrator._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_send_and_reply(text),
                orchestrator._loop
            )

    async def _async_send_and_reply(self, text: str) -> None:
        from app.core.orchestrator import orchestrator
        try:
            reply = await orchestrator.process_user_message(text, from_voice=False)
            signal_bridge.emit_ai_response(reply)
        except Exception as e:
            logger.error(f"Erro ao processar envio de texto: {e}")
            signal_bridge.emit_ai_response(f"Desculpe, ocorreu um erro: {e}")
        finally:
            self._restore_input()

    def _restore_input(self) -> None:
        QTimer.singleShot(0, lambda: self.msg_input.setEnabled(True))
        QTimer.singleShot(0, lambda: self.send_btn.setEnabled(True))
        QTimer.singleShot(0, lambda: self.msg_input.setFocus())

    def _analyze_screen(self) -> None:
        self.msg_input.setText("O que está aberto na minha tela?")
        self._send_message()

    def _on_user_message_received(self, text: str) -> None:
        self.conversation.add_message(role="user", text=text)

    def _on_ai_response_received(self, text: str) -> None:
        self.conversation.add_message(role="assistant", text=text)

    def _on_state_changed(self, new_state: JarvisState, reason: str) -> None:
        color_map = {
            JarvisState.IDLE: ("#10b981", "Pronto"),
            JarvisState.LISTENING: ("#00d2ff", "Ouvindo..."),
            JarvisState.THINKING: ("#fbbf24", "Pensando..."),
            JarvisState.SPEAKING: ("#a855f7", "Falando..."),
            JarvisState.EXECUTING_TOOL: ("#f97316", "Executando Ferramenta..."),
            JarvisState.WATCHING: ("#06b6d4", "Analisando Visão..."),
            JarvisState.ERROR: ("#ef4444", "Erro"),
            JarvisState.OFFLINE: ("#64748b", "Offline"),
        }
        color, label = color_map.get(new_state, ("#94a3b8", new_state.value))
        self.status_lbl.setText(f"● {label} ({reason})")
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")

    def open_settings(self) -> None:
        dlg = SettingsWindow(self)
        if dlg.exec():
            self.provider_lbl.setText(f"IA: {app_config.ai.provider.upper()} ({app_config.ai.model})")
            from app.core.orchestrator import orchestrator
            orchestrator.reload_provider()

    def open_memory(self) -> None:
        dlg = MemoryWindow(self)
        dlg.exec()

    def open_history(self) -> None:
        dlg = HistoryWindow(self)
        dlg.exec()
