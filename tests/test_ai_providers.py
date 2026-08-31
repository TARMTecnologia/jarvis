"""
Testes Unitarios para a Camada Multiprovedor de IA com Mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.ai.base_provider import AIProvider, AIResponse, ToolCallRequest
from app.ai.provider_factory import AIProviderFactory
from app.ai.openai_provider import OpenAIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.anthropic_provider import AnthropicProvider


def test_factory_creation():
    prov_openai = AIProviderFactory.create_provider("openai", "gpt-4o-mini", api_key="sk-test")
    assert isinstance(prov_openai, OpenAIProvider)
    assert prov_openai.model == "gpt-4o-mini"

    prov_gemini = AIProviderFactory.create_provider("gemini", "gemini-2.0-flash", api_key="test_key")
    assert isinstance(prov_gemini, GeminiProvider)

    prov_claude = AIProviderFactory.create_provider("claude", "claude-3-5-sonnet-20241022", api_key="sk-ant-test")
    assert isinstance(prov_claude, AnthropicProvider)


def test_openai_tool_formatting():
    prov = OpenAIProvider(api_key="sk-mock", model="gpt-4o-mini")
    raw_tools = [{
        "name": "get_weather",
        "description": "Obtem o clima",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    }]
    formatted = prov.format_tools(raw_tools)
    assert len(formatted) == 1
    assert formatted[0]["type"] == "function"
    assert formatted[0]["function"]["name"] == "get_weather"


def test_claude_tool_formatting():
    prov = AnthropicProvider(api_key="sk-mock", model="claude-3-5-sonnet-20241022")
    raw_tools = [{
        "name": "get_cpu",
        "description": "Uso de CPU",
        "parameters": {"type": "object", "properties": {}}
    }]
    formatted = prov.format_tools(raw_tools)
    assert len(formatted) == 1
    assert formatted[0]["name"] == "get_cpu"
    assert "input_schema" in formatted[0]
