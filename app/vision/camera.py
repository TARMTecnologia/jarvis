"""
Captura de Webcam via OpenCV com Suporte Multi-Backend Resiliente para o JARVIS.
Suporta captura continua desacoplada para a UI e captura instantanea sob demanda para a IA.
"""

import time
import threading
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("vision.camera")


class CameraCapture:
    """Thread de captura contínua e síncrona de frames da webcam."""

    def __init__(self):
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._current_frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[np.ndarray], None]] = []

    @staticmethod
    def _open_capture_device(index: int) -> Optional[cv2.VideoCapture]:
        """Tenta abrir a câmera testando backends compatíveis do Windows (Padrão, MSMF e DSHOW)."""
        backends = [None, cv2.CAP_MSMF, cv2.CAP_DSHOW]
        for b in backends:
            try:
                cap = cv2.VideoCapture(index, b) if b is not None else cv2.VideoCapture(index)
                if cap is not None and cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        return cap
                    cap.release()
            except Exception:
                pass
        return None

    @staticmethod
    def list_cameras(max_tested: int = 3) -> List[Dict[str, Any]]:
        """Lista câmeras de vídeo funcionais disponíveis no sistema."""
        available = []
        for index in range(max_tested):
            try:
                cap = CameraCapture._open_capture_device(index)
                if cap is not None and cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
                    available.append({
                        "index": index,
                        "name": f"Camera {index} ({w}x{h})"
                    })
                    cap.release()
            except Exception as e:
                logger.debug(f"Erro ao listar camera {index}: {e}")
        return available

    def start(self, camera_index: Optional[int] = None) -> bool:
        """Inicia a captura da câmera na thread de background."""
        with self._lock:
            if self._is_running:
                return True

            idx = camera_index if camera_index is not None else app_config.vision.camera_index

            try:
                self._cap = self._open_capture_device(idx)
                if self._cap is None:
                    if idx != 0:
                        self._cap = self._open_capture_device(0)

                if self._cap is None or not self._cap.isOpened():
                    logger.warning(f"Não foi possível abrir a câmera índice {idx}.")
                    return False

                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, app_config.vision.resolution_width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, app_config.vision.resolution_height)

                self._is_running = True
                self._thread = threading.Thread(target=self._capture_loop, daemon=True)
                self._thread.start()
                logger.info(f"Captura de camera iniciada com sucesso (indice: {idx}).")
                return True

            except Exception as e:
                logger.error(f"Falha ao iniciar camera: {e}")
                self._is_running = False
                return False

    def stop(self) -> None:
        """Interrompe a captura e libera os recursos de hardware."""
        with self._lock:
            self._is_running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        with self._lock:
            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception as e:
                    logger.debug(f"Erro ao liberar camera: {e}")
                self._cap = None
            self._current_frame = None
            logger.info("Camera liberada e desativada.")

    def _capture_loop(self) -> None:
        """Loop contínuo de captura na taxa de quadros do preview."""
        fps_target = app_config.vision.preview_fps
        frame_interval = 1.0 / max(1, fps_target)

        while self._is_running and self._cap is not None and self._cap.isOpened():
            start_t = time.time()
            ret, frame = self._cap.read()

            if ret and frame is not None:
                with self._lock:
                    self._current_frame = frame

                for cb in self._callbacks:
                    try:
                        cb(frame)
                    except Exception as e:
                        logger.error(f"Erro no callback de camera: {e}")

            elapsed = time.time() - start_t
            sleep_time = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_time)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Retorna uma cópia do frame mais recente capturado."""
        with self._lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
        return None

    def capture_frame_sync(self, camera_index: Optional[int] = None) -> Optional[np.ndarray]:
        """Captura um frame instantâneo de forma síncrona com auto-exposição garantida."""
        latest = self.get_latest_frame()
        if latest is not None:
            return latest

        idx = camera_index if camera_index is not None else app_config.vision.camera_index
        cap = self._open_capture_device(idx) or self._open_capture_device(0)
        if cap is None:
            return None

        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, app_config.vision.resolution_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, app_config.vision.resolution_height)
            
            frame = None
            for _ in range(4):
                ret, f = cap.read()
                if ret and f is not None:
                    frame = f
                time.sleep(0.05)

            return frame
        finally:
            cap.release()

    def add_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    @property
    def is_running(self) -> bool:
        return self._is_running


camera_capture = CameraCapture()
