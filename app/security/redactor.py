"""
Redator e Mascarador Automatico de Dados Sensiveis para o JARVIS.
Inspirado na protecao de privacidade 100% local do isair/jarvis.
Mascara senhas, chaves de API, CPFs e cartoes de credito antes de salvar em disco.
"""

import re
from typing import Optional

# Padroes regex para deteccao de dados sensiveis
API_KEY_PATTERNS = [
    re.compile(r"\b(sk-[A-Za-z0-9\-_]{20,})\b"),           # OpenAI API Keys
    re.compile(r"\b(ghp_[A-Za-z0-9]{30,})\b"),            # GitHub Personal Access Tokens
    re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b"),          # Google Gemini / Cloud API Keys
    re.compile(r"\b(sk-ant-[A-Za-z0-9\-_]{30,})\b"),      # Anthropic Claude Keys
    re.compile(r"(?i)\b(bearer\s+[A-Za-z0-9\-_\.]{20,})\b") # Bearer Tokens
]

CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
CPF_PATTERN = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
PASSWORD_PATTERN = re.compile(r"(?i)(?:senha|password|passwd|pin)\s*(?:[=:]|\s+eh|\s+[eé])\s*([^\s,;]+)")


class SensitiveDataRedactor:
    """Motor de mascaramento e higienização de textos confidenciais."""

    @staticmethod
    def redact(text: Optional[str]) -> str:
        """Substitui dados sigilosos por tags de mascaramento seguro."""
        if not text:
            return ""

        redacted = text

        # 1. Chaves de API
        for pat in API_KEY_PATTERNS:
            redacted = pat.sub("[CHAVE_API_REDACTADA]", redacted)

        # 2. Cartoes de Credito (apenas se tiver entre 13 e 16 digitos validos)
        def _mask_cc(match):
            digits = re.sub(r"\D", "", match.group(0))
            if 13 <= len(digits) <= 16:
                return f"[CARTAO_FINAL_{digits[-4:]}]"
            return match.group(0)

        redacted = CREDIT_CARD_PATTERN.sub(_mask_cc, redacted)

        # 3. CPFs Brasileiros
        def _mask_cpf(match):
            digits = re.sub(r"\D", "", match.group(0))
            if len(digits) == 11:
                return f"[CPF_FINAL_{digits[-2:]}]"
            return match.group(0)

        redacted = CPF_PATTERN.sub(_mask_cpf, redacted)

        # 4. Senhas Explicitas
        redacted = PASSWORD_PATTERN.sub(r"senha: [SENHA_PROTEGIDA]", redacted)

        return redacted


sensitive_redactor = SensitiveDataRedactor()
