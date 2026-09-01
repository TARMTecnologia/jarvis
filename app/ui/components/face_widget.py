"""
Widget de Rosto Robótico Low-Poly Futurista para o JARVIS.
Inspirado na interface do isair/jarvis com estética wireframe neon, brilho âmbar/dourado e animações orgânicas de respiração, olhar, anéis de escuta, spinner de pensamento e ondas sonoras na boca.
"""

import math
import random
import time
from typing import List, Tuple, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath, QLinearGradient, QRadialGradient
from PySide6.QtCore import Qt, QTimer, QPointF
from app.core.state_machine import state_machine, JarvisState
from app.core.event_bus import event_bus, EventType


class LowPolyFaceWidget(QWidget):
    """
    Rosto robótico holográfico low-poly renderizado em tempo real via QPainter.
    Reage visualmente a todos os estados operacionais do JARVIS.
    """

    # Cores Tema JARVIS / Âmbar Futurista
    PRIMARY_COLOR = QColor("#00d2ff")       # Ciano / Holograma (ou Dourado #fbbf24)
    SECONDARY_COLOR = QColor("#0088cc")     # Ciano escuro
    GLOW_COLOR = QColor("#55e6ff")          # Brilho de alta intensidade
    AMBER_PRIMARY = QColor("#fbbf24")       # Âmbar Stark
    AMBER_GLOW = QColor("#fcd34d")
    BG_COLOR = QColor("#06080d")

    def __init__(self, parent=None, use_amber: bool = True):
        super().__init__(parent)
        self.setMinimumSize(280, 280)

        self.use_amber = use_amber
        self.primary_col = self.AMBER_PRIMARY if use_amber else self.PRIMARY_COLOR
        self.glow_col = self.AMBER_GLOW if use_amber else self.GLOW_COLOR

        # Estado atual
        self._current_state = state_machine.current_state
        self._is_blinking = False
        self._blink_progress = 0.0

        # Animações de Respiração e Olhar
        self._breathing_time = 0.0
        self._breathing_scale = 1.0
        self._gaze_x = 0.0
        self._gaze_y = 0.0
        self._target_gaze_x = 0.0
        self._target_gaze_y = 0.0
        self._head_tilt = 0.0

        # Efeitos de Estado
        self._spinner_angle = 0.0           # Thinking
        self._waveform_time = 0.0           # Speaking
        self._listening_rings: List[float] = [] # Listening

        # Conecta aos eventos do sistema
        state_machine.add_callback(self._on_state_changed)
        event_bus.subscribe(EventType.AUDIO_LEVEL_CHANGED, self._on_audio_level)

        # Timer de Animação (~30 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(33)

        self._schedule_next_blink()
        self._schedule_next_gaze()

    def _schedule_next_blink(self):
        interval = random.randint(2500, 5500)
        QTimer.singleShot(interval, self._start_blink)

    def _start_blink(self):
        if not self._is_blinking:
            self._is_blinking = True
            self._blink_progress = 0.0
        self._schedule_next_blink()

    def _schedule_next_gaze(self):
        interval = random.randint(1800, 4500)
        QTimer.singleShot(interval, self._shift_gaze)

    def _shift_gaze(self):
        self._target_gaze_x = random.uniform(-1.0, 1.0)
        self._target_gaze_y = random.uniform(-0.5, 0.5)
        self._head_tilt = random.uniform(-2.5, 2.5)
        self._schedule_next_gaze()

    def _on_state_changed(self, new_state: JarvisState, reason: str):
        self._current_state = new_state
        if new_state == JarvisState.LISTENING:
            self._listening_rings = [0.0]

    def _on_audio_level(self, event):
        pass

    def _animate(self):
        # 1. Respiração Orgânica
        self._breathing_time += 0.04
        self._breathing_scale = 1.0 + 0.025 * math.sin(self._breathing_time)

        # 2. Piscar de Olhos
        if self._is_blinking:
            self._blink_progress += 0.15
            if self._blink_progress >= 1.0:
                self._is_blinking = False
                self._blink_progress = 0.0

        # 3. Interpolação suave de olhar
        self._gaze_x += (self._target_gaze_x - self._gaze_x) * 0.08
        self._gaze_y += (self._target_gaze_y - self._gaze_y) * 0.08

        # 4. Estado Thinking (Spinner girando)
        if self._current_state in (JarvisState.THINKING, JarvisState.EXECUTING_TOOL):
            self._spinner_angle = (self._spinner_angle + 8.0) % 360.0

        # 5. Estado Speaking (Waveform da boca)
        if self._current_state == JarvisState.SPEAKING:
            self._waveform_time += 0.25

        # 6. Estado Listening (Anéis em expansão)
        if self._current_state == JarvisState.LISTENING:
            new_rings = []
            for r in self._listening_rings:
                nr = r + 0.035
                if nr < 1.0:
                    new_rings.append(nr)
            if not new_rings or new_rings[-1] > 0.35:
                new_rings.append(0.0)
            self._listening_rings = new_rings
        else:
            self._listening_rings = []

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        size = min(w, h) * 0.40 * self._breathing_scale

        painter.translate(cx, cy + self._gaze_y * 8.0)
        painter.rotate(self._head_tilt)

        # 1. Anéis de Escuta (Listening Echo Rings)
        if self._listening_rings:
            for r in self._listening_rings:
                alpha = int(220 * (1.0 - r))
                ring_pen = QPen(QColor(self.glow_col.red(), self.glow_col.green(), self.glow_col.blue(), alpha), 2)
                painter.setPen(ring_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                rw = size * (1.0 + r * 0.8)
                rh = size * 1.25 * (1.0 + r * 0.8)
                painter.drawEllipse(QPointF(0, 0), rw, rh)

        # 2. Contorno Estrutural Low-Poly da Cabeça
        head_pen = QPen(self.primary_col, 2)
        painter.setPen(head_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        head_points = [
            QPointF(-size * 0.65, -size * 0.90),  # Topo Esquerdo
            QPointF(0.0, -size * 1.15),           # Topo Centro
            QPointF(size * 0.65, -size * 0.90),   # Topo Direito
            QPointF(size * 0.85, -size * 0.20),   # Têmpora Direita
            QPointF(size * 0.60, size * 0.65),    # Mandíbula Direita
            QPointF(0.0, size * 1.10),            # Queixo
            QPointF(-size * 0.60, size * 0.65),   # Mandíbula Esquerda
            QPointF(-size * 0.85, -size * 0.20),  # Têmpora Esquerda
        ]

        # Desenha polígono da cabeça
        path = QPainterPath()
        path.moveTo(head_points[0])
        for pt in head_points[1:]:
            path.lineTo(pt)
        path.closeSubpath()
        painter.drawPath(path)

        # 3. Linhas Geométricas Faciais (Wireframe Low-Poly)
        wire_pen = QPen(QColor(self.primary_col.red(), self.primary_col.green(), self.primary_col.blue(), 90), 1)
        painter.setPen(wire_pen)

        # Linhas da testa ao nariz
        painter.drawLine(head_points[1], QPointF(0, -size * 0.10))
        painter.drawLine(head_points[0], QPointF(-size * 0.35, -size * 0.25))
        painter.drawLine(head_points[2], QPointF(size * 0.35, -size * 0.25))
        painter.drawLine(head_points[7], QPointF(-size * 0.35, -size * 0.25))
        painter.drawLine(head_points[3], QPointF(size * 0.35, -size * 0.25))
        painter.drawLine(QPointF(-size * 0.35, -size * 0.25), QPointF(0, -size * 0.10))
        painter.drawLine(QPointF(size * 0.35, -size * 0.25), QPointF(0, -size * 0.10))
        painter.drawLine(QPointF(0, -size * 0.10), QPointF(0, size * 0.35))
        painter.drawLine(QPointF(0, size * 0.35), head_points[5])
        painter.drawLine(QPointF(-size * 0.60, size * 0.65), QPointF(0, size * 0.35))
        painter.drawLine(QPointF(size * 0.60, size * 0.65), QPointF(0, size * 0.35))

        # 4. Olhos Holográficos
        eye_y = -size * 0.28
        eye_spacing = size * 0.38
        eye_w = size * 0.22
        eye_h = size * 0.14

        # Piscar
        if self._is_blinking:
            blink_factor = math.sin(self._blink_progress * math.pi)
            eye_h = max(2.0, eye_h * (1.0 - blink_factor * 0.95))

        self._draw_eye(painter, -eye_spacing + self._gaze_x * 4.0, eye_y, eye_w, eye_h, is_left=True)
        self._draw_eye(painter, eye_spacing + self._gaze_x * 4.0, eye_y, eye_w, eye_h, is_left=False)

        # 5. Boca Holográfica / Onda Sonora
        mouth_y = size * 0.55
        mouth_w = size * 0.55

        if self._current_state == JarvisState.SPEAKING:
            # Onda sonora fluida multicamada
            wave_path = QPainterPath()
            points_count = 32
            dx = mouth_w / points_count
            start_x = -mouth_w / 2.0

            wave_path.moveTo(start_x, mouth_y)
            for i in range(points_count + 1):
                px = start_x + i * dx
                norm_i = (i / points_count) * math.pi
                taper = math.sin(norm_i)  # Taper nas pontas
                py = mouth_y + math.sin(self._waveform_time + i * 0.6) * 14.0 * taper + math.cos(self._waveform_time * 1.5 + i * 0.4) * 6.0 * taper
                wave_path.lineTo(px, py)

            speak_pen = QPen(self.glow_col, 2.5)
            painter.setPen(speak_pen)
            painter.drawPath(wave_path)
        else:
            # Boca geométrica estática relaxada
            painter.setPen(QPen(self.primary_col, 2))
            painter.drawLine(QPointF(-mouth_w * 0.4, mouth_y), QPointF(0, mouth_y + 3.0))
            painter.drawLine(QPointF(0, mouth_y + 3.0), QPointF(mouth_w * 0.4, mouth_y))

    def _draw_eye(self, painter: QPainter, x: float, y: float, w: float, h: float, is_left: bool):
        """Desenha olho robótico geométrico com suporte a pupila normal ou spinner de thinking."""
        eye_pen = QPen(self.glow_col, 2)
        painter.setPen(eye_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Contorno geométrico angular do olho
        eye_path = QPainterPath()
        eye_path.moveTo(x - w / 2.0, y)
        eye_path.lineTo(x, y - h / 2.0)
        eye_path.lineTo(x + w / 2.0, y)
        eye_path.lineTo(x, y + h / 2.0)
        eye_path.closeSubpath()
        painter.drawPath(eye_path)

        if self._is_blinking and self._blink_progress > 0.4:
            return

        # Pupila / Spinner
        if self._current_state in (JarvisState.THINKING, JarvisState.EXECUTING_TOOL):
            # Spinner rotativo futurista
            painter.save()
            painter.translate(x, y)
            painter.rotate(self._spinner_angle if is_left else -self._spinner_angle)
            spin_pen = QPen(self.glow_col, 2)
            painter.setPen(spin_pen)
            rad = min(w, h) * 0.65
            painter.drawArc(int(-rad), int(-rad), int(rad * 2), int(rad * 2), 0 * 16, 80 * 16)
            painter.drawArc(int(-rad), int(-rad), int(rad * 2), int(rad * 2), 120 * 16, 80 * 16)
            painter.drawArc(int(-rad), int(-rad), int(rad * 2), int(rad * 2), 240 * 16, 80 * 16)
            painter.restore()
        else:
            # Pupila brilhante com olhar dinâmico
            pupil_x = x + self._gaze_x * (w * 0.22)
            pupil_y = y + self._gaze_y * (h * 0.22)
            painter.setBrush(QBrush(self.glow_col))
            painter.drawEllipse(QPointF(pupil_x, pupil_y), w * 0.18, h * 0.28)
