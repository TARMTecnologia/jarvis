"""
Detector de Palavra de Ativacao (Wake Word) Local para o JARVIS.
Suporta os modos: Wake Word ("Jarvis"), Conversacao Continua e Push-to-Talk.
"""

import re
from typing import Optional, Tuple
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.wakeword")

STOP_COMMANDS = [
    re.compile(r"^(?:jarvis,?\s*)?(?:pare|parar|silencio|silncio|cancelar|cala\s*a\s*boca|quieto|stop)\.?$", re.IGNORECASE),
    re.compile(r"\b(?:pare|silencio|cancelar)\b", re.IGNORECASE)
]


class WakeWordDetector:
    """Gerencia a deteccao local de palavras de ativacao e comandos de parada."""

    def __init__(self, wake_word: str = "Jarvis"):
        self.wake_word = wake_word.strip().lower()
        self._pattern = re.compile(rf"\b{re.escape(self.wake_word)}\b", re.IGNORECASE)

    def is_stop_command(self, text: str) -> bool:
        """Verifica se o texto e uma ordem direta de cancelamento/interrupcao da fala."""
        clean = text.strip().lower()
        for pat in STOP_COMMANDS:
            if pat.search(clean):
                return True
        return False

    def process_transcription(self, text: str, mode: Optional[str] = None) -> Tuple[bool, str]:
        """
        Processa a transcricao do usuario de acordo com o modo de voz configurado.
        Retorna:
          (is_activated: bool, prompt_limpo: str)
        """
        active_mode = mode or app_config.audio.voice_mode
        clean_text = text.strip()

        if not clean_text:
            return False, ""

        # Modo 1: Push to Talk (sempre ativado quando disparado)
        if active_mode == "push_to_talk":
            return True, clean_text

        # Modo 2: Conversacao Continua (qualquer fala ativa o assistente)
        if active_mode == "continuous":
            # Remove a palavra Jarvis se o usuario tiver dito no inicio
            stripped = self._pattern.sub("", clean_text).strip(", ").strip()
            return True, stripped or clean_text

        # Modo 3: Wake Word ("Jarvis")
        if self._pattern.search(clean_text):
            # Remove a palavra wake word do inicio do prompt
            stripped = self._pattern.sub("", clean_text).strip(", ").strip()
            logger.info(f"Wake word '{self.wake_word}' detectada! Prompt extraido: '{stripped}'")
            return True, stripped

        return False, ""


wake_word_detector = WakeWordDetector(wake_word=app_config.audio.wake_word)
