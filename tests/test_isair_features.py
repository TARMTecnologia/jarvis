"""
Testes Unitarios para as Funcionalidades Inspiradas no isair/jarvis.
"""

import pytest
from app.security.redactor import sensitive_redactor
from app.tools.weather_tools import get_weather
from app.automation.dictation import dictation_manager
from app.ai.ollama_provider import OllamaProvider


def test_sensitive_data_redaction():
    # 1. Chaves de API
    raw = "Minha chave OpenAI é sk-1234567890abcdef1234567890abcdef e do github ghp_1234567890abcdef1234567890abcdef"
    redacted = sensitive_redactor.redact(raw)
    assert "sk-" not in redacted
    assert "ghp_" not in redacted
    assert "[CHAVE_API_REDACTADA]" in redacted

    # 2. Cartao de Credito
    raw_cc = "Meu cartao é 4111 2222 3333 4444 para compras"
    redacted_cc = sensitive_redactor.redact(raw_cc)
    assert "4111 2222" not in redacted_cc
    assert "[CARTAO_FINAL_4444]" in redacted_cc

    # 3. CPF
    raw_cpf = "Meu CPF é 123.456.789-00"
    redacted_cpf = sensitive_redactor.redact(raw_cpf)
    assert "123.456.789" not in redacted_cpf
    assert "[CPF_FINAL_00]" in redacted_cpf


def test_weather_tool():
    res = get_weather(city="Rio de Janeiro")
    assert res.get("status") == "success"
    assert "Rio de Janeiro" in res.get("location", "")
    assert "temperature" in res
    assert "condition" in res


def test_dictation_manager():
    dictation_manager.stop()
    assert dictation_manager.is_active is False
    dictation_manager.start()
    assert dictation_manager.is_active is True
    dictation_manager.stop()
    assert dictation_manager.is_active is False


def test_ollama_provider_tool_formatting():
    provider = OllamaProvider(model="llama3.2:latest")
    tools = [{
        "name": "get_weather",
        "description": "Busca clima",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}
    }]
    formatted = provider.format_tools(tools)
    assert len(formatted) == 1
    assert formatted[0]["type"] == "function"
    assert formatted[0]["function"]["name"] == "get_weather"
