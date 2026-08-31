"""
Widget Central do ORB Animado do JARVIS.
Renderiza particulas, aneis orbitais e pulsos de voz em tempo real com QPainter e suporte thread-safe via SignalBridge.
"""

import math
import time
from typing import Optional
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QPen, QBrush, QPainterPath
)
from PySide6.QtWidgets import QWidget
from app.core.state_machine import state_machine, JarvisState
from app.ui.components.signal_bridge import signal_bridge


class OrbWidget(QWidget):
    """Elemento visual futurista reativo ao estado do assistente e nivel de audio."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self.setMaximumSize(280, 280)

        self._state = state_machine.current_state
        self._audio_rms: float = 0.0
        self._phase: float = 0.0
        self._pulse_size: float = 0.0

        # Conecta via SignalBridge (seguranca de thread na GUI)
        signal_bridge.sig_state_changed.connect(self._on_state_changed_str)
        signal_bridge.sig_audio_level.connect(self._on_audio_level_float)

        # Timer de renderizacao a ~45 FPS
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(22)

    def _on_state_changed_str(self, old_state_val: str, new_state_val: str) -> None:
        try:
            self._state = JarvisState(new_state_val)
        except Exception:
            self._state = JarvisState.IDLE
        self.update()

    def _on_audio_level_float(self, raw_rms: float) -> None:
        self._audio_rms = self._audio_rms * 0.7 + min(1.0, raw_rms * 12.0) * 0.3

    def _update_animation(self) -> None:
        self._phase += 0.04
        if self._phase > math.pi * 200:
            self._phase = 0.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        base_radius = min(w, h) * 0.32

        # 1. Paleta de Cores de acordo com o Estado
        if self._state == JarvisState.LISTENING:
            core_color = QColor(0, 210, 255)       # Ciano Eletrico
            glow_color = QColor(0, 255, 200, 160)
            status_text = "● OUVINDO..."
        elif self._state == JarvisState.THINKING:
            core_color = QColor(168, 85, 247)     # Roxo Neon
            glow_color = QColor(217, 70, 239, 160)
            status_text = "● PROCESSANDO..."
        elif self._state == JarvisState.SPEAKING:
            core_color = QColor(56, 189, 248)      # Azul Vibrante
            glow_color = QColor(0, 210, 255, 180)
            status_text = "● FALANDO..."
        elif self._state == JarvisState.EXECUTING_TOOL:
            core_color = QColor(245, 158, 11)     # Dourado HUD
            glow_color = QColor(251, 191, 36, 160)
            status_text = "● EXECUTANDO AÇÃO..."
        elif self._state == JarvisState.WATCHING:
            core_color = QColor(6, 182, 212)       # Ciano Optico
            glow_color = QColor(34, 211, 238, 180)
            status_text = "● OBSERVANDO..."
        elif self._state == JarvisState.ERROR:
            core_color = QColor(239, 68, 68)       # Vermelho Alerta
            glow_color = QColor(248, 113, 113, 160)
            status_text = "● ERRO"
        elif self._state == JarvisState.OFFLINE:
            core_color = QColor(100, 116, 139)     # Cinza Standby
            glow_color = QColor(148, 163, 184, 80)
            status_text = "● OFFLINE"
        else:  # IDLE
            core_color = QColor(0, 180, 216)       # Ciano Suave
            glow_color = QColor(0, 210, 255, 100)
            status_text = "● AGUARDANDO COMANDO"

        # 2. Brilho Radial Externo
        pulsing_r = base_radius + math.sin(self._phase * 1.5) * 4.0
        if self._state in (JarvisState.LISTENING, JarvisState.SPEAKING):
            pulsing_r += self._audio_rms * 25.0

        outer_grad = QRadialGradient(cx, cy, pulsing_r * 1.8)
        outer_grad.setColorAt(0.0, glow_color)
        outer_grad.setColorAt(0.5, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 30))
        outer_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(outer_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), pulsing_r * 1.8, pulsing_r * 1.8)

        # 3. Aneis Orbitais Concentricos Giratorios
        ring_count = 3
        for i in range(ring_count):
            speed_mult = (i + 1) * 0.7 * (-1 if i % 2 == 1 else 1)
            ring_r = base_radius * (1.15 + i * 0.22)
            
            pen = QPen(QColor(core_color.red(), core_color.green(), core_color.blue(), 140 - i * 35))
            pen.setWidthF(1.5)
            pen.setDashPattern([4 + i * 2, 8 + i * 4])
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            painter.save()
            painter.translate(cx, cy)
            painter.rotate((self._phase * 40 * speed_mult) % 360)
            painter.drawEllipse(QPointF(0, 0), ring_r, ring_r)
            painter.restore()

        # 4. Nucleo Central do Orb
        core_grad = QRadialGradient(cx, cy, pulsing_r)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        core_grad.setColorAt(0.3, core_color)
        core_grad.setColorAt(0.8, QColor(core_color.red(), core_color.green(), core_color.blue(), 180))
        core_grad.setColorAt(1.0, QColor(core_color.red(), core_color.green(), core_color.blue(), 40))

        painter.setBrush(QBrush(core_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawEllipse(QPointF(cx, cy), pulsing_r * 0.75, pulsing_r * 0.75)

        # 5. Efeito Especial de Scanner quando estiver em WATCHING
        if self._state == JarvisState.WATCHING:
            scan_y = cy + math.sin(self._phase * 3.0) * (pulsing_r * 0.6)
            scan_pen = QPen(QColor(0, 255, 255, 220), 2.0)
            painter.setPen(scan_pen)
            scan_w = math.sqrt(max(0.0, (pulsing_r * 0.75)**2 - (scan_y - cy)**2))
            painter.drawLine(QPointF(cx - scan_w, scan_y), QPointF(cx + scan_w, scan_y))

        # 6. Texto de Status Inferior
        painter.setPen(QColor(200, 230, 255, 220))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(0, h - 22, w, 20), Qt.AlignmentFlag.AlignCenter, status_text)
