"""
Processamento e Compressao de Frames de Video para o JARVIS.
Converte formatos OpenCV (BGR), JPEG comprimido em RAM e QImage para a UI.
"""

import io
import cv2
import numpy as np
from typing import Optional, Tuple
from PySide6.QtGui import QImage, QPixmap
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("vision.frame_processor")


class FrameProcessor:
    """Utilitários de manipulação e compressão de imagens."""

    @staticmethod
    def resize_frame(frame: np.ndarray, max_width: int = 640, max_height: int = 480) -> np.ndarray:
        """Redimensiona o frame mantendo a proporção de aspecto."""
        h, w = frame.shape[:2]
        if w <= max_width and h <= max_height:
            return frame

        scale = min(max_width / w, max_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    @staticmethod
    def compress_to_jpeg_bytes(frame: np.ndarray, quality: int = 75) -> Optional[bytes]:
        """Comprime o frame OpenCV BGR em bytes JPEG em memória RAM."""
        try:
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            ret, buf = cv2.imencode(".jpg", frame, encode_params)
            if ret:
                return buf.tobytes()
            return None
        except Exception as e:
            logger.error(f"Erro ao comprimir frame em JPEG: {e}")
            return None

    @staticmethod
    def bgr_to_qimage(frame: np.ndarray) -> Optional[QImage]:
        """Converte frame OpenCV (BGR) em QImage para exibição direta em widgets PySide6."""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            return QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        except Exception as e:
            logger.error(f"Erro na conversao BGR para QImage: {e}")
            return None


frame_processor = FrameProcessor()
