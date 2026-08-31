"""
Motor Hibrido de Transcricao de Fala (Speech-To-Text) para o JARVIS.
Suporta Whisper Local (Faster-Whisper int8) e OpenAI Whisper Cloud (whisper-1) para maxima precisao.
"""

import io
import time
import wave
import numpy as np
from typing import Optional
from app.core.config import app_config
from app.security.secrets import secrets_manager
from app.core.logging_config import get_logger

logger = get_logger("audio.stt")


class LocalSTT:
    """Motor de transcricao de voz com suporte a normalizacao de ganho e fallback de alta precisao."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        self._is_loading = False

    def initialize(self) -> bool:
        """Carrega o modelo Faster-Whisper na memoria."""
        if self._model is not None:
            return True

        self._is_loading = True
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Carregando modelo local Faster-Whisper ('{self.model_size}') em CPU/int8...")
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

    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normaliza o ganho do audio para garantir que microfones baixos sejam ouvidos com clareza."""
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()

        max_val = np.max(np.abs(audio_data))
        if max_val > 0.001:
            # Ganho automatico para atingir ~80% do volume maximo sem clipping
            gain = 0.8 / max_val
            # Limita ganho maximo a 15x para evitar amplificar ruido de fundo puro
            gain = min(15.0, max(1.0, gain))
            audio_data = audio_data * gain

        return np.clip(audio_data, -1.0, 1.0)

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcreve um segmento de audio.
        Utiliza OpenAI Whisper Cloud se configurado ou Faster-Whisper Local com ganho dinamico.
        """
        if audio_data is None or len(audio_data) == 0:
            return ""

        # Normaliza ganho do sinal
        norm_audio = self.normalize_audio(audio_data)

        # 1. Se estiver configurado para usar OpenAI Whisper Cloud
        if app_config.audio.stt_engine == "openai_whisper":
            openai_key = secrets_manager.get_api_key("openai")
            if openai_key:
                cloud_text = self._transcribe_openai_cloud(norm_audio, sample_rate, openai_key)
                if cloud_text:
                    return cloud_text
                logger.warning("Falha na transcricao OpenAI Cloud. Usando Whisper Local como fallback.")

        # 2. Transcricao Local via Faster-Whisper
        return self._transcribe_local(norm_audio, sample_rate)

    def _transcribe_local(self, norm_audio: np.ndarray, sample_rate: int) -> str:
        """Transcricao local 100% offline."""
        if self._model is None:
            if not self.initialize():
                return ""

        try:
            start_t = time.time()
            segments, info = self._model.transcribe(
                norm_audio,
                language="pt",
                beam_size=5,
                initial_prompt="Transcrição em português brasileiro de conversa com o assistente inteligente Jarvis.",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
                condition_on_previous_text=False
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts).strip()
            duration = time.time() - start_t
            logger.info(f"Transcricao Local Whisper ({duration:.2f}s): '{full_text}'")
            return full_text

        except Exception as e:
            logger.error(f"Erro na transcricao Local Whisper: {e}")
            return ""

    def _transcribe_openai_cloud(self, norm_audio: np.ndarray, sample_rate: int, api_key: str) -> Optional[str]:
        """Transcricao de altissima precisao via OpenAI Whisper API (whisper-1)."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # Converte float32 em WAV PCM 16-bit em memoria
            int_audio = (norm_audio * 32767.0).astype(np.int16)
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(int_audio.tobytes())

            wav_buf.seek(0)
            wav_buf.name = "audio.wav"

            start_t = time.time()
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=wav_buf,
                language="pt",
                prompt="Assistente pessoal Jarvis conversando em português brasileiro."
            )
            duration = time.time() - start_t
            text = transcript.text.strip()
            logger.info(f"Transcricao OpenAI Whisper Cloud ({duration:.2f}s): '{text}'")
            return text

        except Exception as e:
            logger.error(f"Erro ao transcrever via OpenAI Whisper API: {e}")
            return None


local_stt = LocalSTT(model_size=app_config.audio.stt_model_size)
