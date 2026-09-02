"""
Detector de Atividade de Voz (VAD) Inteligente com Supressao Adaptativa de Ruido de Fundo para o JARVIS.
Permite pausas naturais na fala (ate 2.0s) sem cortar a frase pela metade e filtra estalos, ventiladores e respiracao.
"""

import time
import numpy as np
from typing import Callable, List, Optional
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.vad")


class VoiceActivityDetector:
    """Detecta fala humana autentica, permitindo pausas naturais e eliminando ruidos da sala."""

    def __init__(
        self,
        base_energy_threshold: float = 0.015,
        silence_duration_ms: int = 2000,
        sample_rate: int = 16000
    ):
        self.base_energy_threshold = base_energy_threshold
        self.silence_duration_ms = silence_duration_ms
        self.sample_rate = sample_rate

        self._is_speaking = False
        self._speech_buffer: List[np.ndarray] = []
        self._pre_speech_buffer: List[np.ndarray] = []
        self._last_speech_time: float = 0.0
        self._speech_start_time: float = 0.0
        self._ambient_noise_rms: float = 0.005

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
        """Processa um chunk de audio vindo do microfone com cancelamento de ruido adaptativo."""
        now = time.time()

        # Rastreia o piso de ruido do ambiente quando nao esta em fala ativa
        if not self._is_speaking:
            self._ambient_noise_rms = 0.96 * self._ambient_noise_rms + 0.04 * max(0.001, rms)

        # Limiar dinamico: precisa estar significativamente acima do ruido continuo da sala
        dynamic_threshold = max(
            self.base_energy_threshold * (1.6 - app_config.audio.vad_sensitivity),
            self._ambient_noise_rms * 2.8
        )

        # Buffer circular de pre-fala (600ms para nunca perder a primeira silaba)
        self._pre_speech_buffer.append(frame)
        if len(self._pre_speech_buffer) > 12:
            self._pre_speech_buffer.pop(0)

        if rms >= dynamic_threshold:
            self._last_speech_time = now

            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_time = now
                self._speech_buffer = list(self._pre_speech_buffer)
                logger.debug(f"Inicio de fala detectado pelo VAD (RMS={rms:.4f}, Piso Ruido={self._ambient_noise_rms:.4f}).")
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

            # So finaliza a fala se houver silencio continuo de 2.0s (permite pausas para respirar e pensar)
            if silence_ms >= target_silence:
                self._is_speaking = False
                speech_duration = now - self._speech_start_time

                # Ignora estalos, tossidas rapidas e ruidos menores que 700ms
                if speech_duration >= 0.7 and len(self._speech_buffer) > 0:
                    audio_segment = np.concatenate(self._speech_buffer, axis=0)
                    segment_rms = float(np.sqrt(np.mean(audio_segment ** 2)))
                    
                    # Filtra ruidos muito fracos que nao constituem voz
                    if segment_rms > 0.008:
                        logger.info(f"Fim de fala confirmado (duracao: {speech_duration:.2f}s, RMS={segment_rms:.4f}).")
                        if self._on_speech_finished:
                            try:
                                self._on_speech_finished(audio_segment)
                            except Exception as e:
                                logger.error(f"Erro no callback on_speech_finished: {e}")
                    else:
                        logger.debug("Segmento de audio descartado por baixa energia vocal.")

                self._speech_buffer.clear()

    def reset(self) -> None:
        """Reinicia o estado interno do VAD."""
        self._is_speaking = False
        self._speech_buffer.clear()
        self._pre_speech_buffer.clear()


vad_detector = VoiceActivityDetector()
