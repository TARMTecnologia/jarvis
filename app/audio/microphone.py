"""
Captura e Monitoramento de Microfone para o JARVIS.
Gerencia dispositivos de entrada, calcula niveis RMS e envia streaming de chunks.
"""

import threading
import time
import numpy as np
from typing import List, Dict, Any, Optional, Callable
import sounddevice as sd
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.microphone")


class MicrophoneManager:
    """Gerencia a captura contínua de áudio do microfone com sounddevice."""

    def __init__(self, sample_rate: int = 16000, block_size: int = 1024):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._callbacks: List[Callable[[np.ndarray, float], None]] = []
        self._lock = threading.Lock()
        self._current_rms: float = 0.0

    @staticmethod
    def list_input_devices() -> List[Dict[str, Any]]:
        """Lista todos os microfones/dispositivos de entrada de áudio disponíveis."""
        devices = []
        try:
            hostapis = sd.query_hostapis()
            all_devs = sd.query_devices()
            for idx, dev in enumerate(all_devs):
                if dev["max_input_channels"] > 0:
                    api_name = hostapis[dev["hostapi"]]["name"] if dev["hostapi"] < len(hostapis) else ""
                    devices.append({
                        "index": idx,
                        "name": f"{dev['name']} ({api_name})",
                        "channels": dev["max_input_channels"],
                        "default_samplerate": dev["default_samplerate"]
                    })
        except Exception as e:
            logger.error(f"Erro ao listar microfones: {e}")
        return devices

    def start(self, device_index: Optional[int] = None) -> bool:
        """Inicia a captura contínua do microfone em background."""
        with self._lock:
            if self._is_recording:
                return True

            dev_idx = device_index if device_index is not None else app_config.audio.input_device_index
            
            try:
                self._stream = sd.InputStream(
                    device=dev_idx,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=self.block_size,
                    callback=self._audio_callback
                )
                self._stream.start()
                self._is_recording = True
                logger.info(f"Microfone iniciado (dispositivo: {dev_idx}, taxa: {self.sample_rate}Hz).")
                return True
            except Exception as e:
                logger.error(f"Falha ao iniciar microfone: {e}")
                self._is_recording = False
                return False

    def stop(self) -> None:
        """Interrompe a captura do microfone."""
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.debug(f"Erro ao fechar stream de microfone: {e}")
                self._stream = None
            self._current_rms = 0.0
            logger.info("Microfone desativado.")

    def add_callback(self, callback: Callable[[np.ndarray, float], None]) -> None:
        """Adiciona função ouvinte que recebe cada chunk de áudio e seu nível RMS."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[np.ndarray, float], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: sd.CallbackFlags) -> None:
        """Callback executado pela thread de áudio do sounddevice."""
        if not self._is_recording:
            return

        # Calcula RMS (Root Mean Square) do sinal para VU Meter e VAD
        rms = float(np.sqrt(np.mean(indata ** 2)))
        self._current_rms = rms

        for cb in self._callbacks:
            try:
                cb(indata.copy(), rms)
            except Exception as e:
                logger.error(f"Erro no callback de microfone: {e}")

    @property
    def current_rms(self) -> float:
        return self._current_rms

    @property
    def is_recording(self) -> bool:
        return self._is_recording


microphone = MicrophoneManager()
