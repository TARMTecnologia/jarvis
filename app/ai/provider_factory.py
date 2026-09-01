"""
Fabrica de Provedores de IA do JARVIS.
Instancia e configura o provedor correto com base nas configuracoes e chaves seguras.
"""

from typing import Optional
from app.ai.base_provider import AIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.ollama_provider import OllamaProvider
from app.security.secrets import secrets_manager
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("ai.factory")


class AIProviderFactory:
    """Fabrica para instanciar provedores de IA de forma desacoplada."""

    @staticmethod
    def create_provider(
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> AIProvider:
        """
        Cria e retorna uma instancia do provedor especificado.
        Se nenhum parametro for passado, utiliza a configuracao ativa do app.
        """
        name = (provider_name or app_config.ai.provider).strip().lower()
        model = model_name or app_config.ai.model or app_config.get_default_model_for_provider(name)
        key = api_key or secrets_manager.get_api_key(name)

        logger.info(f"Criando AIProvider para: '{name}' com modelo: '{model}'")

        if name == "openai":
            return OpenAIProvider(api_key=key, model=model)
        elif name == "gemini":
            return GeminiProvider(api_key=key, model=model)
        elif name in ("anthropic", "claude"):
            return AnthropicProvider(api_key=key, model=model)
        elif name in ("ollama", "local", "lmstudio"):
            return OllamaProvider(api_key=key, model=model)
        else:
            logger.warning(f"Provedor desconhecido '{name}'. Usando OpenAI como fallback padrao.")
            return OpenAIProvider(api_key=key, model="gpt-4o-mini")
