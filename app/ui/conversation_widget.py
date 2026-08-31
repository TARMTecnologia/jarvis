"""
Widget de Conversacao e Historico de Mensagens com Baloes Estilizados para o JARVIS.
"""

import time
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton, QSizePolicy
)
import pyperclip


class MessageBubble(QFrame):
    """Balao individual de mensagem do usuario ou do assistente."""

    def __init__(self, role: str, text: str, timestamp_str: Optional[str] = None, parent: QWidget = None):
        super().__init__(parent)
        self.role = role.lower()
        time_text = timestamp_str or time.strftime("%H:%M")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)

        # 1. Cabecalho do balao
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        sender_name = "VOCÊ" if self.role == "user" else "JARVIS"
        sender_color = "#38bdf8" if self.role == "user" else "#00d2ff"

        sender_label = QLabel(sender_name)
        sender_label.setStyleSheet(f"color: {sender_color}; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(sender_label)

        time_label = QLabel(time_text)
        time_label.setStyleSheet("color: #64748b; font-size: 10px;")
        header_layout.addWidget(time_label)

        header_layout.addStretch()

        copy_btn = QPushButton("Copiar")
        copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: none;
                font-size: 10px;
                padding: 0px 4px;
                min-height: 14px;
            }
            QPushButton:hover {
                color: #00d2ff;
            }
        """)
        copy_btn.clicked.connect(lambda: pyperclip.copy(text))
        header_layout.addWidget(copy_btn)

        main_layout.addLayout(header_layout)

        # 2. Conteudo do texto
        content_label = QLabel(text)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_label.setStyleSheet("color: #f1f5f9; font-size: 13px; line-height: 1.4;")
        main_layout.addWidget(content_label)

        # 3. Estilizacao do balao
        if self.role == "user":
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #1e1b4b;
                    border: 1px solid #4338ca;
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #0f172a;
                    border: 1px solid #0284c7;
                    border-radius: 12px;
                }
            """)


class ConversationWidget(QWidget):
    """Area de rolagem contendo as mensagens da conversa atual."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.messages_layout = QVBoxLayout(self.container)
        self.messages_layout.setContentsMargins(8, 8, 8, 8)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.container)
        outer_layout.addWidget(self.scroll_area)

    def add_message(self, role: str, text: str, timestamp_str: Optional[str] = None) -> None:
        """Adiciona uma nova mensagem ao chat e rola para o fim."""
        bubble = MessageBubble(role=role, text=text, timestamp_str=timestamp_str)
        
        # Insere antes do stretch final
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, bubble)

        # Rola para baixo apos atualizar layout
        self.scroll_to_bottom()

    def clear(self) -> None:
        """Limpa todas as mensagens da tela."""
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def scroll_to_bottom(self) -> None:
        # Aguarda layout atualizar e rola
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
