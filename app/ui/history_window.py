"""
Janela de Historico de Conversas do JARVIS.
Permite visualizar conversas anteriores por data e excluir sessoes antigas.
"""

import time
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QPushButton, QMessageBox, QSplitter
)
from app.memory.database import db
from app.ui.styles import HUD_DARK_STYLESHEET


class HistoryWindow(QDialog):
    """Visualizador de conversas e turnos passados."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS — Histórico de Conversas")
        self.resize(780, 500)
        self.setStyleSheet(HUD_DARK_STYLESHEET)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Splitter com lista a esquerda e mensagens a direita
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Lista de Conversas
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Sessões Anteriores:"))
        self.conv_list = QListWidget()
        self.conv_list.itemClicked.connect(self._on_conversation_selected)
        left_layout.addWidget(self.conv_list)

        self.delete_btn = QPushButton("Excluir Sessão")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.clicked.connect(self._delete_selected)
        left_layout.addWidget(self.delete_btn)

        splitter.addWidget(left_widget)

        # 2. Painel de Mensagens
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("Mensagens da Sessão:"))
        self.msg_viewer = QTextEdit()
        self.msg_viewer.setReadOnly(True)
        self.msg_viewer.setStyleSheet("background-color: #06080d; font-size: 13px; line-height: 1.4;")
        right_layout.addWidget(self.msg_viewer)

        splitter.addWidget(right_widget)
        splitter.setSizes([260, 520])
        main_layout.addWidget(splitter)

        self._load_conversations()

    def _load_conversations(self) -> None:
        self.conv_list.clear()
        conn = db.get_connection()
        cursor = conn.execute("""
            SELECT id, title, created_at, message_count
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT 50
        """)

        for row in cursor.fetchall():
            date_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(row["created_at"]))
            item_text = f"{row['title']}\n({date_str} - {row['message_count']} msgs)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.conv_list.addItem(item)

    def _on_conversation_selected(self, item: QListWidgetItem) -> None:
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        conn = db.get_connection()
        cursor = conn.execute("""
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, (conv_id,))

        self.msg_viewer.clear()
        for row in cursor.fetchall():
            sender = "VOCÊ" if row["role"] == "user" else "JARVIS"
            color = "#38bdf8" if row["role"] == "user" else "#00d2ff"
            t_str = time.strftime("%H:%M", time.localtime(row["created_at"]))

            self.msg_viewer.append(f"<b style='color: {color};'>[{sender} - {t_str}]</b>")
            self.msg_viewer.append(f"<p style='color: #f1f5f9; margin-bottom: 12px;'>{row['content']}</p>")

    def _delete_selected(self) -> None:
        item = self.conv_list.currentItem()
        if not item:
            return

        conv_id = item.data(Qt.ItemDataRole.UserRole)
        conn = db.get_connection()
        with conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))

        self.msg_viewer.clear()
        self._load_conversations()
