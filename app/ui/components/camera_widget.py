"""
Widget de Visualizacao e Controle da Webcam (Os Olhos do JARVIS) para o HUD.
Renderiza o feed de video ao vivo com auto-inicializacao, reticulo HUD e botoes para registro facial e captura de foto.
"""

import time
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from app.vision.vision_manager import vision_manager
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("ui.camera_widget")


class CameraWidget(QWidget):
    """Widget de visualizacao HUD da Webcam com scanlines e reticulo tatico."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 240)
        self._is_active = False

        self._setup_ui()

        # Auto-inicia a camera se habilitada nas configuracoes
        if getattr(app_config.vision, "enabled", True):
            success = vision_manager.start_camera()
            if success:
                self._is_active = True
                self.btn_toggle.setText("Desligar Câmera")

        # Timer de atualizacao do feed (30 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        self._timer.start(33)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Frame de exibição do vídeo
        self.video_frame = QLabel()
        self.video_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_frame.setStyleSheet("""
            QLabel {
                background-color: #030712;
                border: 1px solid #1e293b;
                border-radius: 8px;
                color: #64748b;
                font-size: 12px;
            }
        """)
        self.video_frame.setText("📷 Inicializando sensores ópticos do JARVIS...")
        layout.addWidget(self.video_frame, stretch=1)

        # Barra de Controles
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(6)

        self.btn_toggle = QPushButton("Ligar Câmera")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #fbbf24;
            }
        """)
        self.btn_toggle.clicked.connect(self._toggle_camera)
        ctrl_layout.addWidget(self.btn_toggle)

        self.btn_photo = QPushButton("Tirar Foto")
        self.btn_photo.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
        """)
        self.btn_photo.clicked.connect(self._take_photo)
        ctrl_layout.addWidget(self.btn_photo)

        layout.addLayout(ctrl_layout)

    def _toggle_camera(self) -> None:
        """Liga ou desliga a webcam."""
        if self._is_active:
            vision_manager.stop_camera()
            self._is_active = False
            self.btn_toggle.setText("Ligar Câmera")
            self.video_frame.setText("📷 Câmera Desligada")
        else:
            success = vision_manager.start_camera()
            if success:
                self._is_active = True
                self.btn_toggle.setText("Desligar Câmera")
            else:
                self.video_frame.setText("❌ Falha ao acessar Webcam")

    def _take_photo(self) -> None:
        """Captura foto e salva na Área de Trabalho."""
        if not self._is_active:
            vision_manager.start_camera()
            self._is_active = True
            self.btn_toggle.setText("Desligar Câmera")
        
        res = vision_manager.take_photo(save_to_desktop=True)
        if res.get("status") == "success":
            self.video_frame.setText(f"✅ Foto Salva no Desktop!")
            QTimer.singleShot(2000, lambda: None)

    def _update_frame(self) -> None:
        """Obtém imagem da webcam e renderiza na interface com HUD ao vivo."""
        if not vision_manager.is_active:
            return

        qimg = vision_manager.get_preview_image()
        if qimg and not qimg.isNull():
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(
                self.video_frame.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_frame.setPixmap(scaled)
