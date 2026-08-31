"""
Configuração central de logging para o JARVIS.
Inclui rotação automática de arquivos e filtro de proteção contra vazamento de segredos (API keys).
"""

import os
import re
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Padrões conhecidos de chaves de API para higienização
SENSITIVE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),          # OpenAI
    re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.IGNORECASE),          # Google API Key
    re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),      # Anthropic
    re.compile(r"(api[_\-]?key\s*[:=]\s*['\"]?)([^'\"\s]+)", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*['\"]?)([^'\"\s]+)", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Filtra e mascara credenciais e chaves de API das mensagens de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.sanitize(record.msg)
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self.sanitize(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        return True

    @staticmethod
    def sanitize(text: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub("[REDACTED_SECRET]", text)
        return text


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> None:
    """Configura os handlers de console e arquivo rotativo."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "jarvis.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Evita duplicação de handlers se já configurado
    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    sensitive_filter = SensitiveDataFilter()

    # Handler para Console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    root_logger.addHandler(console_handler)

    # Handler Rotativo de Arquivo (Máximo 5MB por arquivo, até 5 backups)
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sensitive_filter)
    root_logger.addHandler(file_handler)

    logging.info("Sistema de logging do JARVIS inicializado com sucesso.")


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado para o módulo."""
    return logging.getLogger(f"jarvis.{name}")
