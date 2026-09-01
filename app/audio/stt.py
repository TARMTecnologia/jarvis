"""
Motor Hibrido de Transcricao de Fala (Speech-To-Text) para o JARVIS.
Suporta Whisper Local (Faster-Whisper int8 100% Offline) e OpenAI Whisper Cloud com filtro rigido de ruidos e alucinacoes (como amara.org, legendas, etc).
"""

import io
import re
import time
import wave
import numpy as np
from typing import Optional
from app.core.config import app_config
from app.security.secrets import secrets_manager
from app.core.logging_config import get_logger

logger = get_logger("audio.stt")

# Filtros para alucinacoes comuns do Whisper geradas por ruido de ar/microfone
HALLUCINATION_PATTERNS = [
    re.compile(r".*amara\.org.*", re.IGNORECASE),
    re.compile(r".*comunidade\s+da\s+amara.*", re.IGNORECASE),
    re.compile(r".*legendas\s+(?:pela|por|feitas|de).*", re.IGNORECASE),
    re.compile(r".*subt[ií]tulos.*", re.IGNORECASE),
    re.compile(r".*transcri[cç][aã]o\s+(?:feita|por|autom[aá]tica).*", re.IGNORECASE),
    re.compile(r".*obrigado\s+por\s+assistir.*", re.IGNORECASE),
    re.compile(r".*inscreva-?se\s+no\s+canal.*", re.IGNORECASE),
    re.compile(r".*deixe\s+o\s+like.*", re.IGNORECASE),
    re.compile(r"^\s*\[(?:m[uú]sica|ru[ií]do|aplausos|sil[eê]ncio|som|risos|m[uú]sica\s+de\s+fundo)\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*[.,;:!?_\-\s]+\s*$"),
    re.compile(r"^\s*(?:you|thank\s+you|bye|subtitles|welcome)\.?\s*$", re.IGNORECASE)
]


class LocalSTT:
    """Motor de transcricao de voz de alta fidelidade com ganho adaptativo e filtro de ruidos."""

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
        """Normaliza o ganho do audio para garantir que sussurros ou microfones baixos sejam ouvidos com clareza."""
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()

        sig = np.nan_to_num(audio_data, nan=0.0)
        max_val = float(np.max(np.abs(sig)))
        if max_val > 0.0005:
            gain = 0.85 / max_val
            gain = min(20.0, max(1.0, gain))
            sig = sig * gain

        return np.clip(sig, -1.0, 1.0)

    def _is_hallucination(self, text: str) -> bool:
        """Verifica se o texto retornado e apenas uma alucinacao de ruido de fundo."""
        if not text or len(text.strip()) < 2:
            return True
        for pat in HALLUCINATION_PATTERNS:
            if pat.search(text.strip()):
                return True
        return False

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcreve um segmento de audio.
        Utiliza OpenAI Whisper Cloud se configurado ou Faster-Whisper Local com filtragem estrita.
        """
        if audio_data is None or len(audio_data) == 0:
            return ""

        # Verifica energia do sinal (se for ruido absoluto puro, descarta)
        rms = float(np.sqrt(np.mean(audio_data ** 2)))
        if rms < 0.002:
            logger.debug(f"Segmento de audio com energia muito baixa ({rms:.5f}), descartado.")
            return ""

        norm_audio = self.normalize_audio(audio_data)

        # 1. Se estiver configurado para OpenAI Whisper Cloud com chave valida
        if app_config.audio.stt_engine == "openai_whisper":
            openai_key = secrets_manager.get_api_key("openai")
            if openai_key:
                cloud_text = self._transcribe_openai_cloud(norm_audio, sample_rate, openai_key)
                if cloud_text and cloud_text.strip() and not self._is_hallucination(cloud_text):
                    return cloud_text
                logger.warning("Transcricao OpenAI Cloud vazia ou ruido. Usando Whisper Local.")

        # 2. Transcricao Local via Faster-Whisper
        raw_text = self._transcribe_local(norm_audio, sample_rate)
        if self._is_hallucination(raw_text):
            logger.debug(f"Alucinacao de ruido descartada: '{raw_text}'")
            return ""
        return raw_text

    def _transcribe_local(self, norm_audio: np.ndarray, sample_rate: int) -> str:
        """Transcricao local 100% offline e sem descarte indevido de audio."""
        if self._model is None:
            if not self.initialize():
                return ""

        try:
            start_t = time.time()
            segments, info = self._model.transcribe(
                norm_audio,
                language="pt",
                beam_size=5,
                temperature=[0.0, 0.2, 0.4],
                vad_filter=False,
                initial_prompt="Conversa em português brasileiro com o assistente Jarvis.",
                condition_on_previous_text=False
            )

            text_parts = []
            for segment in segments:
                t = segment.text.strip()
                if t:
                    text_parts.append(t)

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
