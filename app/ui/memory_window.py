"""
Janela de Gerenciamento Visual de Memorias do JARVIS.
Permite pesquisar, filtrar por tipo, adicionar, editar, excluir e exportar memorias semanticas.
"""

import time
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QInputDialog, QFileDialog
)
from app.memory.long_term import long_term_memory
from app.memory.models import MemoryType, MemoryRecord
from app.ui.styles import HUD_DARK_STYLESHEET


class MemoryWindow(QDialog):
    """Interface para consulta e administracao da memoria permanente."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS — Gerenciador de Memória")
        self.resize(800, 520)
        self.setStyleSheet(HUD_DARK_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Cabecalho com busca e filtro
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar memórias...")
        self.search_input.textChanged.connect(self._load_memories)
        top_layout.addWidget(self.search_input)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["Todos", "semantic", "preference", "fact", "project", "episodic"])
        self.type_filter.currentTextChanged.connect(self._load_memories)
        top_layout.addWidget(self.type_filter)

        self.add_btn = QPushButton("+ Nova Memória")
        self.add_btn.setProperty("class", "primary")
        self.add_btn.clicked.connect(self._add_memory)
        top_layout.addWidget(self.add_btn)

        layout.addLayout(top_layout)

        # 2. Tabela de Memorias
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Conteúdo da Memória", "Tipo", "Importância"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # 3. Botoes de Acao (Editar, Excluir, Exportar)
        actions_layout = QHBoxLayout()

        self.edit_btn = QPushButton("Editar Selecionada")
        self.edit_btn.clicked.connect(self._edit_memory)
        actions_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Excluir Selecionada")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.clicked.connect(self._delete_memory)
        actions_layout.addWidget(self.delete_btn)

        actions_layout.addStretch()

        self.export_btn = QPushButton("Exportar (JSON/TXT)")
        self.export_btn.clicked.connect(self._export_memories)
        actions_layout.addWidget(self.export_btn)

        self.clear_all_btn = QPushButton("Apagar Tudo")
        self.clear_all_btn.setProperty("class", "danger")
        self.clear_all_btn.clicked.connect(self._clear_all)
        actions_layout.addWidget(self.clear_all_btn)

        layout.addLayout(actions_layout)

        # Carrega dados iniciais
        self._load_memories()

    def _load_memories(self) -> None:
        """Carrega e popula as linhas da tabela."""
        query = self.search_input.text().strip()
        mtype = self.type_filter.currentText()

        memories = long_term_memory.list_memories(
            search_query=query if query else None,
            memory_type=mtype if mtype != "Todos" else None
        )

        self.table.setRowCount(len(memories))
        for row, mem in enumerate(memories):
            id_item = QTableWidgetItem(mem.id[:8] + "...")
            id_item.setData(Qt.ItemDataRole.UserRole, mem.id)

            text_item = QTableWidgetItem(mem.text)
            type_item = QTableWidgetItem(mem.memory_type.value)
            imp_item = QTableWidgetItem(f"{mem.importance}/5")

            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, text_item)
            self.table.setItem(row, 2, type_item)
            self.table.setItem(row, 3, imp_item)

    def _get_selected_memory_id(self) -> Optional[str]:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Aviso", "Selecione uma memória na tabela.")
            return None
        row = selected[0].row()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def _add_memory(self) -> None:
        text, ok = QInputDialog.getText(self, "Nova Memória", "Informe o fato ou preferência para o JARVIS lembrar:")
        if ok and text.strip():
            long_term_memory.add_memory(text=text.strip(), memory_type=MemoryType.FACT, importance=4)
            self._load_memories()

    def _edit_memory(self) -> None:
        mid = self._get_selected_memory_id()
        if not mid:
            return

        mem = long_term_memory.get_memory(mid)
        if not mem:
            return

        new_text, ok = QInputDialog.getText(self, "Editar Memória", "Atualize o texto da memória:", text=mem.text)
        if ok and new_text.strip():
            long_term_memory.update_memory(memory_id=mid, text=new_text.strip())
            self._load_memories()

    def _delete_memory(self) -> None:
        mid = self._get_selected_memory_id()
        if not mid:
            return

        reply = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            "Deseja excluir esta memória permanentemente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            long_term_memory.delete_memory(mid)
            self._load_memories()

    def _clear_all(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Deseja apagar TODAS as memórias salvas no banco?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            long_term_memory.delete_all_memories()
            self._load_memories()

    def _export_memories(self) -> None:
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar Memórias",
            "memorias_jarvis.json",
            "JSON (*.json);;Texto (*.txt)"
        )
        if not file_path:
            return

        fmt = "txt" if file_path.endswith(".txt") else "json"
        content = long_term_memory.export_memories(export_format=fmt)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(self, "Sucesso", f"Memórias exportadas com sucesso para:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao exportar arquivo: {e}")
