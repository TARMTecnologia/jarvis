"""
Visualizador de Nivel de Microfone (VU Meter) para o JARVIS.
"""

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QWidget
from app.core.event_bus import event_bus, EventType, Event


class AudioVisualizerWidget(QWidget):
    """Barra horizontal com segmentos luminosos indicando o nivel de volume do microfone."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setFixedHeight(12)
        self.setMinimumWidth(120)
        self._level: float = 0.0

        event_bus.subscribe(EventType.AUDIO_LEVEL_CHANGED, self._on_audio_level)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._decay)
        self._timer.start(30)

    def _on_audio_level(self, event: Event) -> None:
        raw_rms = event.data.get("rms", 0.0)
        norm = min(1.0, raw_rms * 15.0)
        if norm > self._level:
            self._level = norm

    def _decay(self) -> None:
        if self._level > 0.01:
            self._level *= 0.88
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bars = 16
        spacing = 3
        bar_w = (w - (bars - 1) * spacing) / bars

        active_bars = int(self._level * bars)

        for i in range(bars):
            x = i * (bar_w + spacing)
            if i < active_bars:
                # Gradiente verde -> ciano -> vermelho
                if i < bars * 0.6:
                    color = QColor(0, 210, 255)
                elif i < bars * 0.85:
                    color = QColor(250, 204, 21)
                else:
                    color = QColor(239, 68, 68)
            else:
                color = QColor(30, 41, 59, 120)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, 1, bar_w, h - 2), 2, 2)
