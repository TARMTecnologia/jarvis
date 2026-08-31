"""
Detector Inteligente de Mudanca de Cena para o JARVIS.
Evita envio repetitivo de frames identicos para a IA calculando a diferenca visual entre quadros.
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("vision.scene_detection")


class SceneDetector:
    """Calcula alteração perceptual de cena entre frames subsequentes."""

    def __init__(self, change_threshold: float = 0.15):
        self.change_threshold = change_threshold
        self._last_gray_frame: Optional[np.ndarray] = None

    def has_scene_changed(self, current_frame: np.ndarray) -> Tuple[bool, float]:
        """
        Compara o frame atual com o anterior.
        Retorna (mudou_significativamente, diferenca_normalizada).
        """
        if current_frame is None:
            return False, 0.0

        # Redimensiona para uma escala pequena (128x96) e converte para tons de cinza
        small = cv2.resize(current_frame, (128, 96))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        # Suavização Gaussiana para remover ruído de sensor
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if self._last_gray_frame is None:
            self._last_gray_frame = gray
            return True, 1.0  # Primeiro frame é sempre considerado novo

        # Calcula a diferença absoluta de pixels
        diff = cv2.absdiff(self._last_gray_frame, gray)
        non_zero_ratio = float(np.count_nonzero(diff > 25)) / (128 * 96)

        self._last_gray_frame = gray
        has_changed = non_zero_ratio >= self.change_threshold

        logger.debug(f"Variacao de cena: {non_zero_ratio:.3f} (limiar: {self.change_threshold}) -> Mudou: {has_changed}")
        return has_changed, non_zero_ratio

    def reset(self) -> None:
        """Reseta o histórico de frames de referência."""
        self._last_gray_frame = None


scene_detector = SceneDetector(change_threshold=app_config.vision.scene_change_threshold)
