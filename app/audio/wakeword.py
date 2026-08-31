"""
Detector de Palavra de Ativacao (Wake Word) e Comandos de Voz do JARVIS.
Detecta a palavra de ativacao "Jarvis" (com tolerancia fonetica), modos continuo/push-to-talk e comandos de interrupcao.
"""

import re
from typing import Optional, Tuple
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.wakeword")

# Padrao regex com tolerancia fonetica para "Jarvis"
WAKE_WORD_PATTERN = re.compile(
    r"(?:e\s+a[ií]|ei|oi|ol[aá]|fala|por\s+favor\s+)?\b(jarvis|i[aá]rvis|jarves|jarvys|jarve|j[aá]rvis)\b",
    re.IGNORECASE
)

# Comandos de parada imediata (Barge-in)
STOP_COMMAND_PATTERN = re.compile(
    r"\b(jarvis,?\s*)?(pare|parar|sil[eê]ncio|chega|cancele?|desligar?|calado|para\s+de\s+falar)\b",
    re.IGNORECASE
)


class WakeWordDetector:
    """Valida se o texto transcrito contem a palavra de ativacao ou comandos de controle."""

    def __init__(self, default_wake_word: str = "Jarvis"):
        self.default_wake_word = default_wake_word

    def is_stop_command(self, text: str) -> bool:
        """Verifica se o usuario ordenou interrupcao imediata da fala do Jarvis."""
        if not text:
            return False
        return bool(STOP_COMMAND_PATTERN.search(text.strip()))

    def check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Verifica a presenca da palavra de ativacao no texto transcrito.
        Retorna (detectado: bool, texto_limpo: str).
        """
        if not text or not text.strip():
            return False, ""

        clean_text = text.strip()
        voice_mode = app_config.audio.voice_mode

        # 1. Modo Continuo ou Push-to-Talk: qualquer fala e considerada valida
        if voice_mode in ("continuous", "push_to_talk"):
            # Remove a palavra "Jarvis" se o usuario falou por habito
            cleaned = WAKE_WORD_PATTERN.sub("", clean_text).strip()
            # Limpa virgulas ou dois pontos no inicio
            cleaned = re.sub(r"^[,.:\- ]+", "", cleaned).strip()
            return True, cleaned if cleaned else clean_text

        # 2. Modo Wake Word: exige a palavra "Jarvis"
        match = WAKE_WORD_PATTERN.search(clean_text)
        if match:
            # Extrai o comando apos a palavra de ativacao
            idx_end = match.end()
            prompt = clean_text[idx_end:].strip()
            prompt = re.sub(r"^[,.:\- ]+", "", prompt).strip()

            logger.info(f"Wake word detectada! Prompt extraido: '{prompt}'")
            return True, prompt

        return False, ""


wake_word_detector = WakeWordDetector()
