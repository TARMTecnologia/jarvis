"""
Detector de Palavra de Ativacao (Wake Word), Janela de Conversa Continua (Hot Window) e Comandos de Parada do JARVIS.
"""

import re
import time
from typing import Optional, Tuple
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.wakeword")

# Padrao regex com ampla tolerancia fonetica para "Jarvis"
WAKE_WORD_PATTERN = re.compile(
    r"(?:e\s+a[ií]|ei|oi|ol[aá]|fala|por\s+favor\s+)?\b(jarvis|i[aá]rvis|jarves|jarvys|jarve|j[aá]rvis|jarvi)\b",
    re.IGNORECASE
)

# Comandos de parada imediata (Barge-in verbal: "pare jarvis", "jarvis pare", "silêncio", "pare", "stop", etc.)
STOP_COMMAND_PATTERN = re.compile(
    r"\b(jarvis,?\s*)?(pare|parar|sil[eê]ncio|chega|cancele?|desligar?|calado|para\s+de\s+falar|stop|para|cala\s+a\s+boca)(,?\s*jarvis)?\b",
    re.IGNORECASE
)


class WakeWordDetector:
    """Valida palavra de ativacao em qualquer posicao e gerencia janela de continuacao de dialogo e comandos de parada."""

    def __init__(self, default_wake_word: str = "Jarvis"):
        self.default_wake_word = default_wake_word
        self._followup_until: float = 0.0

    def is_stop_command(self, text: str) -> bool:
        """Verifica se o usuario ordenou interrupcao imediata da fala do Jarvis."""
        if not text:
            return False
        return bool(STOP_COMMAND_PATTERN.search(text.strip()))

    def start_followup_window(self, duration_sec: float = 8.0) -> None:
        """Abre janela de conversa contínua após a fala do JARVIS."""
        self._followup_until = time.time() + duration_sec
        logger.debug(f"Janela de conversa contínua aberta por {duration_sec}s.")

    def is_in_followup_window(self) -> bool:
        """Verifica se ainda estamos dentro da janela de conversa contínua."""
        return time.time() < self._followup_until

    def reset_followup(self) -> None:
        self._followup_until = 0.0

    def check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Verifica se a fala e direcionada ao Jarvis (por Wake Word em qualquer lugar ou janela de continuacao).
        Retorna (detectado: bool, texto_limpo: str).
        """
        if not text or not text.strip():
            return False, ""

        clean_text = text.strip()
        voice_mode = app_config.audio.voice_mode

        # 1. Modo Continuo ou Push-to-Talk
        if voice_mode in ("continuous", "push_to_talk"):
            cleaned = WAKE_WORD_PATTERN.sub("", clean_text).strip()
            cleaned = re.sub(r"^[,.:\- ]+|[,.:\- ]+$", "", cleaned).strip()
            return True, cleaned if cleaned else clean_text

        # 2. Janela de Conversa Ativa (Follow-up Hot Window de 8s)
        if self.is_in_followup_window():
            logger.info(f"Fala recebida dentro da janela de conversa contínua: '{clean_text}'")
            cleaned = WAKE_WORD_PATTERN.sub("", clean_text).strip()
            cleaned = re.sub(r"^[,.:\- ]+|[,.:\- ]+$", "", cleaned).strip()
            return True, cleaned if cleaned else clean_text

        # 3. Deteccao de "Jarvis" em qualquer posicao da frase
        match = WAKE_WORD_PATTERN.search(clean_text)
        if match:
            cleaned = WAKE_WORD_PATTERN.sub("", clean_text).strip()
            cleaned = re.sub(r"^[,.:\- ]+|[,.:\- ]+$", "", cleaned).strip()

            if not cleaned:
                cleaned = "Olá Jarvis"

            logger.info(f"Wake word detectada! Prompt extraído: '{cleaned}'")
            return True, cleaned

        return False, ""

    def process_transcription(self, text: str) -> Tuple[bool, str]:
        return self.check_wake_word(text)


wake_word_detector = WakeWordDetector()
