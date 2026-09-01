"""
Testes Unitarios para o Modulo de Configuracao e Secrets do JARVIS.
"""

import pytest
from app.core.config import AppConfig, RECOMMENDED_MODELS
from app.security.secrets import SecretsManager


def test_app_config_defaults():
    config = AppConfig()
    assert config.ai.provider in ("openai", "gemini", "claude", "ollama", "local")
    assert config.audio.voice_mode in ("wakeword", "continuous", "push_to_talk")
    assert config.system.language == "pt-BR"
    assert config.memory.enabled is True


def test_recommended_models_resolution():
    config = AppConfig()
    openai_model = config.get_default_model_for_provider("openai")
    assert "gpt-4" in openai_model

    gemini_model = config.get_default_model_for_provider("gemini")
    assert "gemini" in gemini_model

    claude_model = config.get_default_model_for_provider("claude")
    assert "claude" in claude_model

    ollama_model = config.get_default_model_for_provider("ollama")
    assert "llama" in ollama_model or "deepseek" in ollama_model


def test_secrets_masking():
    sm = SecretsManager()
    assert sm.mask_key(None) == "Não configurada"
    assert sm.mask_key("1234") == "********"
    masked = sm.mask_key("sk-abcdef1234567890xyz")
    assert masked.startswith("sk-a")
    assert masked.endswith("0xyz")
