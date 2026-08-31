"""
Widget de Visualizacao e Controle da Webcam para o JARVIS.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from app.vision.vision_manager import vision_manager


class CameraWidget(QFrame):
    """Painel de visualizacao do feed da camera com controles de privacidade."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("cameraCard")
        self.setStyleSheet("""
            #cameraCard {
                background-color: #0d121d;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Cabecalho
        header_layout = QHBoxLayout()
        self.title_label = QLabel("VISÃO MULTIMODAL")
        self.title_label.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.toggle_btn = QPushButton("DESATIVAR CÂMERA")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                font-size: 10px;
                padding: 4px 10px;
                min-height: 18px;
            }
            QPushButton:hover {
                border: 1px solid #ef4444;
                color: #ef4444;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle_camera)
        header_layout.addWidget(self.toggle_btn)
        layout.addLayout(header_layout)

        # 2. Area de Preview da Imagem
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(240, 160)
        self.preview_label.setMaximumSize(360, 240)
        self.preview_label.setStyleSheet("background-color: #06080d; border-radius: 8px; border: 1px solid #1e293b;")
        self.preview_label.setText("Câmera Desativada\n(Privacidade Garantida)")
        layout.addWidget(self.preview_label)

        # Timer de atualizacao do preview (20 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_preview)
        self._timer.start(50)

    def _toggle_camera(self) -> None:
        active = vision_manager.toggle_camera()
        if active:
            self.toggle_btn.setText("DESATIVAR CÂMERA")
            self.toggle_btn.setStyleSheet("background-color: #1e293b; color: #f8fafc; border: 1px solid #334155;")
        else:
            self.toggle_btn.setText("ATIVAR CÂMERA")
            self.toggle_btn.setStyleSheet("background-color: #064e3b; color: #34d399; border: 1px solid #10b981;")
            self.preview_label.setText("Câmera Desativada\n(Privacidade Garantida)")
            self.preview_label.setPixmap(QPixmap())

    def _update_preview(self) -> None:
        if not vision_manager.is_active:
            return

        qimg = vision_manager.get_preview_image()
        if qimg is not None and not qimg.isNull():
            pix = QPixmap.fromImage(qimg).scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(pix)
