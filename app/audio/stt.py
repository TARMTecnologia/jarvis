"""
Transcricao de Fala Local (Speech-To-Text) para o JARVIS.
Utiliza Faster-Whisper / Whisper local em CPU com int8 para maxima velocidade e privacidade.
"""

import io
import time
import numpy as np
from typing import Optional
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.stt")


class LocalSTT:
    """Motor de transcrição de voz local 100% offline."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        self._is_loading = False

    def initialize(self) -> bool:
        """Carrega o modelo Faster-Whisper na memória."""
        if self._model is not None:
            return True

        self._is_loading = True
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Carregando modelo local Whisper ('{self.model_size}') em CPU/int8...")
            # compute_type="int8" roda muito rápido em qualquer CPU moderna sem sobrecarregar
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                download_root="data/cache/models"
            )
            self._is_loading = False
            logger.info(f"Modelo local Whisper '{self.model_size}' pronto para uso.")
            return True
        except Exception as e:
            logger.error(f"Falha ao carregar Faster-Whisper: {e}")
            self._is_loading = False
            return False

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcreve um segmento de áudio (array numpy 1D float32 a 16kHz).
        Retorna o texto em português transcrito.
        """
        if audio_data is None or len(audio_data) == 0:
            return ""

        if self._model is None:
            if not self.initialize():
                return ""

        try:
            # Garante que os dados estejam em float32 normalizados entre -1.0 e 1.0
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            max_val = np.max(np.abs(audio_data))
            if max_val > 1.0:
                audio_data = audio_data / max_val

            # Apenas 1D
            if audio_data.ndim > 1:
                audio_data = audio_data.flatten()

            start_t = time.time()
            segments, info = self._model.transcribe(
                audio_data,
                language="pt",
                beam_size=3,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts).strip()
            duration = time.time() - start_t
            logger.info(f"Transcricao STT concluida em {duration:.2f}s: '{full_text}'")
            return full_text

        except Exception as e:
            logger.error(f"Erro na transcricao STT: {e}")
            return ""


local_stt = LocalSTT(model_size=app_config.audio.stt_model_size)
