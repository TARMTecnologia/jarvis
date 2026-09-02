"""
Detector de Palavra de Ativacao (Wake Word), Janela de Conversa Continua e Comandos de Parada Rigorosos para o JARVIS.
Garante que frases normais contendo a preposicao "para" NUNCA sejam confundidas com comandos de parada.
"""

import re
import time
from typing import Optional, Tuple
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.wakeword")

# Padrao regex estrito para "Jarvis"
WAKE_WORD_PATTERN = re.compile(
    r"\b(jarvis|i[aá]rvis|jarves|jarvys|jarve|j[aá]rvis|jarvi)\b",
    re.IGNORECASE
)

# Prefixos permitidos antes de "Jarvis"
CLEAN_PREFIX_PATTERN = re.compile(
    r"^(?:e\s+a[ií]|ei|oi|ol[aá]|fala|por\s+favor|bom\s+dia|boa\s+tarde|boa\s+noite)\s+",
    re.IGNORECASE
)

# Comandos de parada ESTRITOS (imperativos curtos como "pare jarvis", "silêncio", "chega", "para de falar")
# NUNCA deve casar com frases normais contendo "para" como preposicao.
STRICT_STOP_PATTERN = re.compile(
    r"^(?:jarvis,?\s*)?(?:pare|parar|sil[eê]ncio|chega|cancele|calado|para\s+de\s+falar|stop|cala\s+a\s+boca|fique\s+quieto)(?:\s+jarvis)?\.?$",
    re.IGNORECASE
)

# Padroes de intencao interrogativa / conversacional direta
CONVERSATIONAL_INTENT_PATTERN = re.compile(
    r"\b(sabe|onde|como|qual|quem|quando|por\s+que|porque|o\s+que|quanto|quantos|me\s+diga|me\s+explica|me\s+ajuda|pesquise|procure|abra|mostre|veja|conte|voc[eê]|ser[aá]|pode|consegue|lembra|escreveu|enviou|apertou)\b|\?",
    re.IGNORECASE
)


class WakeWordDetector:
    """Valida palavra de ativacao, gerencia janela de dialogo contínuo de 25s e responde a perguntas diretas."""

    def __init__(self, default_wake_word: str = "Jarvis"):
        self.default_wake_word = default_wake_word
        self._followup_until: float = 0.0

    def is_stop_command(self, text: str) -> bool:
        """
        Verifica se o usuario ordenou interrupcao imediata da fala do Jarvis.
        Frases com mais de 4 palavras NUNCA sao tratadas como comando de parada isolado.
        """
        if not text or not text.strip():
            return False
        clean = text.strip()
        words = clean.split()
        if len(words) > 4 and not re.search(r"^(?:jarvis,?\s*)?(?:para\s+de\s+falar|cala\s+a\s+boca|pare\s+agora)", clean, re.IGNORECASE):
            return False
        return bool(STRICT_STOP_PATTERN.search(clean))

    def start_followup_window(self, duration_sec: float = 25.0) -> None:
        """Abre janela de conversa contínua estendida após a fala do JARVIS (25 segundos)."""
        self._followup_until = time.time() + duration_sec
        logger.debug(f"Janela de conversa contínua aberta por {duration_sec}s.")

    def is_in_followup_window(self) -> bool:
        """Verifica se ainda estamos dentro da janela de conversa contínua."""
        return time.time() < self._followup_until

    def reset_followup(self) -> None:
        self._followup_until = 0.0

    def check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Verifica se a fala e direcionada ao Jarvis:
        1. Se contem "Jarvis" -> Ativa com prioridade.
        2. Se esta na janela de conversa de 25s -> Ativa sem precisar repetir o nome.
        3. Se for uma pergunta ou dialogo conversacional -> Ativa e responde sem delay.
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

        # 2. Deteccao de "Jarvis" na frase
        match = WAKE_WORD_PATTERN.search(clean_text)
        if match:
            cleaned = WAKE_WORD_PATTERN.sub("", clean_text).strip()
            cleaned = CLEAN_PREFIX_PATTERN.sub("", cleaned).strip()
            cleaned = re.sub(r"^[,.:\- ]+|[,.:\- ]+$", "", cleaned).strip()

            if not cleaned:
                cleaned = "Olá Jarvis"

            logger.info(f"Wake word 'Jarvis' confirmada! Prompt: '{cleaned}'")
            return True, cleaned

        # 3. Janela de Conversa Ativa Estendida (25s)
        if self.is_in_followup_window():
            words = clean_text.split()
            if len(words) >= 2 and len(clean_text) >= 5:
                cleaned = re.sub(r"^[,.:\- ]+|[,.:\- ]+$", "", clean_text).strip()
                logger.info(f"Fala recebida dentro da janela de diálogo de 25s: '{cleaned}'")
                return True, cleaned

        # 4. Reconhecimento de Pergunta ou Diálogo Direto do Mentor
        if len(clean_text.split()) >= 3 and CONVERSATIONAL_INTENT_PATTERN.search(clean_text):
            cleaned = re.sub(r"^[,.:\- ]+|[,.:\- ]+$", "", clean_text).strip()
            logger.info(f"Pergunta/diálogo direto detectado: '{cleaned}'. Ativando resposta!")
            return True, cleaned

        return False, ""

    def process_transcription(self, text: str) -> Tuple[bool, str]:
        return self.check_wake_word(text)


wake_word_detector = WakeWordDetector()
