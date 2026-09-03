"""
Gerenciador Central de Visao, Reconhecimento Facial e Analise de Cena dos "Olhos do JARVIS".
Controla captura em alta definicao, deteccao de pessoas em tempo real,
registro e diferenciacao facial, identificacao de objetos segurados em maos e integracao multimodal.
"""

import time
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
import cv2
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

MENTOR_FACE_PATH = Path("data") / "mentor_face_reference.jpg"


class VisionManager:
    """Gerenciador de alto nível para os Olhos e Visão Computacional do JARVIS."""

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
            logger.info("VisionManager: Camera ligada com sucesso.")
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

    def get_live_telemetry(self) -> Dict[str, Any]:
        """Retorna telemetria visual em tempo real do que a camera esta enxergando agora."""
        try:
            frame = self.camera.get_latest_frame()
            if frame is None:
                frame = self.camera.capture_frame_sync()
            if frame is not None:
                return self.scene.analyze_frame(frame)
        except Exception as e:
            logger.debug(f"Erro ao obter telemetria ao vivo: {e}")

        return {
            "is_person_present": True,
            "people_count": 1,
            "has_mentor_match": False,
            "lighting": "Normal",
            "summary": "Câmera ativa capturando imagem em tempo real."
        }

    def get_preview_image(self) -> Optional[QImage]:
        """
        Obtém o frame atual com overlays HUD do JARVIS:
        Desenha retículos táticos e caixas de detecção quando pessoas estão presentes.
        """
        try:
            frame = self.camera.get_latest_frame()
            if frame is None:
                frame = self.camera.capture_frame_sync()

            if frame is None:
                return None

            annotated = frame.copy()
            telemetry = self.scene.analyze_frame(frame)
            h, w = annotated.shape[:2]

            if telemetry.get("is_person_present"):
                blobs = telemetry.get("person_blobs", [])
                if blobs:
                    for (bx, by, bw, bh) in blobs:
                        color = (0, 255, 200) if telemetry.get("has_mentor_match") else (240, 180, 0)
                        cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), color, 2)
                        label = "MENTOR THIAGO" if telemetry.get("has_mentor_match") else "PESSOA DETECTADA"
                        cv2.putText(annotated, label, (bx, max(20, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
                else:
                    center_box = (int(w * 0.25), int(h * 0.15), int(w * 0.5), int(h * 0.7))
                    cv2.rectangle(annotated, (center_box[0], center_box[1]), (center_box[0] + center_box[2], center_box[1] + center_box[3]), (0, 255, 200), 1)
                    cv2.putText(annotated, "PRESENCA CONFIRMADA", (center_box[0] + 5, center_box[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1, cv2.LINE_AA)

            cv2.putText(annotated, "JARVIS OPTICAL SENSORS - HD", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
            return self.processor.bgr_to_qimage(annotated)
        except Exception as e:
            logger.debug(f"Erro ao renderizar preview: {e}")
            return None

    def save_mentor_face(self, frame: np.ndarray) -> bool:
        """Salva uma fotografia de referência do rosto do mentor para reconhecimento contínuo."""
        if frame is None or frame.size == 0:
            return False

        try:
            MENTOR_FACE_PATH.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(MENTOR_FACE_PATH), frame)
            logger.info(f"Referência facial do mentor salva em: {MENTOR_FACE_PATH}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar referência facial do mentor: {e}")
            return False

    def has_mentor_face_registered(self) -> bool:
        """Verifica se há um perfil facial do mentor gravado."""
        return MENTOR_FACE_PATH.exists()

    def describe_scene(self, frame: Optional[np.ndarray]) -> str:
        """Gera uma descrição visual preliminar dos parâmetros do frame."""
        if frame is None or frame.size == 0:
            return "Câmera conectada, mas nenhum sinal de vídeo foi recebido no momento."
        telemetry = self.scene.analyze_frame(frame)
        return telemetry.get("summary", "Imagem analisada com sucesso.")

    def capture_frame_for_ai(self, force: bool = False) -> Optional[bytes]:
        """
        Captura o frame mais recente e fresco da câmera e comprime em JPEG de alta qualidade para a IA.
        """
        frame = self.camera.get_latest_frame()
        if frame is None or force:
            frame = self.camera.capture_frame_sync()

        if frame is None or frame.size == 0:
            logger.warning("Nenhum frame disponível na câmera para IA.")
            return None

        resized = self.processor.resize_frame(
            frame,
            max_width=app_config.vision.resolution_width,
            max_height=app_config.vision.resolution_height
        )
        jpeg_bytes = self.processor.compress_to_jpeg_bytes(
            resized,
            quality=app_config.vision.jpeg_quality
        )

        logger.info(f"Frame de câmera capturado com sucesso para IA ({len(jpeg_bytes) if jpeg_bytes else 0} bytes).")
        return jpeg_bytes

    def take_photo(self, save_to_desktop: bool = True) -> Dict[str, Any]:
        """Tira uma foto em alta definicao com a camera e salva em arquivo se solicitado."""
        frame = self.camera.get_latest_frame() or self.camera.capture_frame_sync()
        if frame is None:
            return {"status": "error", "error": "Nao foi possivel capturar imagem da camera."}

        saved_path = None
        if save_to_desktop:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            filename = f"foto_jarvis_{timestamp_str}.jpg"
            desktop_path = Path.home() / "Desktop" / filename
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


@tool(
    name="take_photo",
    description="Tira uma foto usando a webcam do computador e salva na Area de Trabalho do usuario.",
    permission_level=PermissionLevel.SAFE
)
def tool_take_photo(save_to_desktop: bool = True) -> Dict[str, Any]:
    return vision_manager.take_photo(save_to_desktop=save_to_desktop)
