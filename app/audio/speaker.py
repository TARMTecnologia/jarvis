"""
Reproducao de Audio com suporte a Barge-In (Interrupcao Instantanea).
"""

import threading
import numpy as np
import sounddevice as sd
from typing import Optional, List, Dict, Any
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.speaker")


class SpeakerManager:
    """Gerencia reproducao de audio e cancelamento imediato."""

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self._is_playing = False
        self._lock = threading.Lock()

    @staticmethod
    def list_output_devices() -> List[Dict[str, Any]]:
        """Lista todos os alto-falantes/dispositivos de saida disponiveis."""
        devices = []
        try:
            hostapis = sd.query_hostapis()
            all_devs = sd.query_devices()
            for idx, dev in enumerate(all_devs):
                if dev["max_output_channels"] > 0:
                    api_name = hostapis[dev["hostapi"]]["name"] if dev["hostapi"] < len(hostapis) else ""
                    devices.append({
                        "index": idx,
                        "name": f"{dev['name']} ({api_name})",
                        "channels": dev["max_output_channels"],
                        "default_samplerate": dev["default_samplerate"]
                    })
        except Exception as e:
            logger.error(f"Erro ao listar alto-falantes: {e}")
        return devices

    def play_numpy(self, audio_data: np.ndarray, sample_rate: Optional[int] = None) -> None:
        """Reproduz um array numpy de audio de forma sincrona/bloqueante na thread chamadora."""
        sr = sample_rate or self.sample_rate
        dev_idx = app_config.audio.output_device_index
        
        with self._lock:
            self._is_playing = True

        try:
            sd.play(audio_data, samplerate=sr, device=dev_idx)
            sd.wait()
        except Exception as e:
            logger.error(f"Erro ao reproduzir audio: {e}")
        finally:
            with self._lock:
                self._is_playing = False

    def stop(self) -> None:
        """Interrompe imediatamente qualquer audio em reproducao (Barge-in)."""
        try:
            sd.stop()
            with self._lock:
                self._is_playing = False
            logger.info("Reproducao de audio interrompida (Barge-in).")
        except Exception as e:
            logger.error(f"Erro ao interromper reproducao: {e}")

    @property
    def is_playing(self) -> bool:
        return self._is_playing


speaker = SpeakerManager()
