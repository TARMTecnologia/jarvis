"""
Detector de Atividade de Voz (VAD) Local para o JARVIS.
Detecta inicio e termino de fala com base em limiar dinamico de energia RMS e janela de silencio aprimorada.
"""

import time
import numpy as np
from typing import Callable, List, Optional
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.vad")


class VoiceActivityDetector:
    """Detecta segmentos de voz ativa a partir do streaming de chunks do microfone."""

    def __init__(
        self,
        energy_threshold: float = 0.008,
        silence_duration_ms: int = 1200,
        sample_rate: int = 16000
    ):
        self.energy_threshold = energy_threshold
        self.silence_duration_ms = silence_duration_ms
        self.sample_rate = sample_rate

        self._is_speaking = False
        self._speech_buffer: List[np.ndarray] = []
        self._pre_speech_buffer: List[np.ndarray] = []
        self._last_speech_time: float = 0.0
        self._speech_start_time: float = 0.0

        # Callbacks
        self._on_speech_started: Optional[Callable[[], None]] = None
        self._on_speech_finished: Optional[Callable[[np.ndarray], None]] = None

    def set_callbacks(
        self,
        on_started: Optional[Callable[[], None]] = None,
        on_finished: Optional[Callable[[np.ndarray], None]] = None
    ) -> None:
        self._on_speech_started = on_started
        self._on_speech_finished = on_finished

    def process_frame(self, frame: np.ndarray, rms: float) -> None:
        """Processa um chunk de audio vindo do microfone."""
        now = time.time()
        # Ajusta sensibilidade com base na configuracao
        threshold = self.energy_threshold * (1.5 - app_config.audio.vad_sensitivity)

        # Buffer circular de pre-fala (aproximadamente 400ms)
        self._pre_speech_buffer.append(frame)
        if len(self._pre_speech_buffer) > 8:
            self._pre_speech_buffer.pop(0)

        if rms >= threshold:
            self._last_speech_time = now

            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_time = now
                self._speech_buffer = list(self._pre_speech_buffer)
                logger.debug("Inicio de fala detectado pelo VAD.")
                if self._on_speech_started:
                    try:
                        self._on_speech_started()
                    except Exception as e:
                        logger.error(f"Erro no callback on_speech_started: {e}")

            self._speech_buffer.append(frame)

        elif self._is_speaking:
            self._speech_buffer.append(frame)
            silence_ms = (now - self._last_speech_time) * 1000
            target_silence = app_config.audio.silence_threshold_ms or self.silence_duration_ms

            if silence_ms >= target_silence:
                self._is_speaking = False
                speech_duration = now - self._speech_start_time

                # Ignora estalos e ruidos menores que 300ms
                if speech_duration >= 0.3 and len(self._speech_buffer) > 0:
                    audio_segment = np.concatenate(self._speech_buffer, axis=0)
                    logger.debug(f"Fim de fala detectado (duracao: {speech_duration:.2f}s, frames: {len(audio_segment)}).")
                    if self._on_speech_finished:
                        try:
                            self._on_speech_finished(audio_segment)
                        except Exception as e:
                            logger.error(f"Erro no callback on_speech_finished: {e}")

                self._speech_buffer.clear()

    def reset(self) -> None:
        """Reinicia o estado interno do VAD."""
        self._is_speaking = False
        self._speech_buffer.clear()
        self._pre_speech_buffer.clear()


vad_detector = VoiceActivityDetector()
