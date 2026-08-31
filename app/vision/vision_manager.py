"""
Gerenciador Central de Visao e Privacidade do JARVIS.
Controla o preview da camera, amostragem inteligente para IA e protecao de privacidade em RAM.
"""

import time
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np
from PySide6.QtGui import QImage
from app.vision.camera import camera_capture, CameraCapture
from app.vision.frame_processor import frame_processor, FrameProcessor
from app.vision.scene_detection import scene_detector, SceneDetector
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.event_bus import event_bus, EventType
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("vision.manager")


class VisionManager:
    """Gerenciador de alto nível para Visão Computacional do JARVIS."""

    def __init__(self):
        self.camera: CameraCapture = camera_capture
        self.processor: FrameProcessor = frame_processor
        self.scene: SceneDetector = scene_detector

        self._last_ai_frame_time: float = 0.0
        self._is_camera_active = False

    def start_camera(self, camera_index: Optional[int] = None) -> bool:
        """Ativa a captura de vídeo da câmera."""
        if self._is_camera_active:
            return True

        success = self.camera.start(camera_index)
        if success:
            self._is_camera_active = True
            event_bus.publish(EventType.CAMERA_STATUS_CHANGED, {"active": True})
            logger.info("VisionManager: Camera ligada.")
        return success

    def stop_camera(self) -> None:
        """Desativa a câmera e libera o hardware (Modo Privacidade)."""
        self._is_camera_active = False
        self.camera.stop()
        self.scene.reset()
        event_bus.publish(EventType.CAMERA_STATUS_CHANGED, {"active": False})
        logger.info("VisionManager: Camera desligada (Modo Privacidade).")

    def toggle_camera(self) -> bool:
        """Alterna o estado da câmera (Liga/Desliga)."""
        if self._is_camera_active:
            self.stop_camera()
            return False
        else:
            return self.start_camera()

    def get_preview_image(self) -> Optional[QImage]:
        """Obtém o frame atual convertido para QImage para exibição no preview da UI."""
        frame = self.camera.get_latest_frame()
        if frame is not None:
            return self.processor.bgr_to_qimage(frame)
        return None

    def capture_frame_for_ai(self, force: bool = False) -> Optional[bytes]:
        """
        Captura um frame comprimido em JPEG para envio a IA.
        Aplica controle de taxa (ai_vision_fps) e deteccao de mudanca de cena para economizar tokens.
        """
        if not self._is_camera_active:
            # Tenta ligar temporariamente se a camera estiver desligada
            if not self.start_camera():
                return None

        frame = self.camera.get_latest_frame()
        if frame is None:
            time.sleep(0.1)
            frame = self.camera.get_latest_frame()
            if frame is None:
                return None

        now = time.time()
        min_interval = 1.0 / max(0.1, app_config.vision.ai_vision_fps)

        if not force and (now - self._last_ai_frame_time) < min_interval:
            # Respeita o limite de FPS da IA
            return None

        # Se amostragem inteligente estiver ativada, verifica se a cena mudou
        if not force and app_config.vision.smart_scene_sampling:
            changed, _ = self.scene.has_scene_changed(frame)
            if not changed:
                return None

        self._last_ai_frame_time = now

        # Redimensiona e comprime em JPEG
        resized = self.processor.resize_frame(
            frame,
            max_width=app_config.vision.resolution_width,
            max_height=app_config.vision.resolution_height
        )
        jpeg_bytes = self.processor.compress_to_jpeg_bytes(
            resized,
            quality=app_config.vision.jpeg_quality
        )

        logger.info(f"Frame capturado para IA ({len(jpeg_bytes) if jpeg_bytes else 0} bytes).")
        return jpeg_bytes

    def take_photo(self, save_to_desktop: bool = True) -> Dict[str, Any]:
        """Tira uma foto em alta definicao com a camera e salva em arquivo se solicitado."""
        if not self._is_camera_active:
            self.start_camera()
            time.sleep(0.3)  # Aguarda auto-exposicao da camera

        frame = self.camera.get_latest_frame()
        if frame is None:
            return {"status": "error", "error": "Nao foi possivel capturar imagem da camera."}

        saved_path = None
        if save_to_desktop:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            filename = f"foto_jarvis_{timestamp_str}.jpg"
            desktop_path = Path.home() / "Desktop" / filename
            import cv2
            cv2.imwrite(str(desktop_path), frame)
            saved_path = str(desktop_path)
            logger.info(f"Foto salva na Area de Trabalho: {saved_path}")

        return {
            "status": "success",
            "saved_to_desktop": save_to_desktop,
            "file_path": saved_path,
            "message": f"Foto capturada com sucesso." + (f" Salva em: {saved_path}" if saved_path else "")
        }

    @property
    def is_active(self) -> bool:
        return self._is_camera_active


vision_manager = VisionManager()


# Registro de Ferramenta Local para IA
@tool(
    name="take_photo",
    description="Tira uma foto usando a webcam do computador e salva na Area de Trabalho do usuario.",
    permission_level=PermissionLevel.SAFE
)
def tool_take_photo(save_to_desktop: bool = True) -> Dict[str, Any]:
    return vision_manager.take_photo(save_to_desktop=save_to_desktop)
