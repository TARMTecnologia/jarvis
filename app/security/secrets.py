"""
Gerenciamento seguro de credenciais e chaves de API utilizando o Windows Credential Locker (keyring)
com suporte a variáveis de ambiente (.env) para desenvolvimento.
"""

import os
from pathlib import Path
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger("security.secrets")

SERVICE_NAME = "JARVIS_AI_ASSISTANT"

# Mapeamento de variáveis de ambiente conhecidas por provedor
PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


def _load_env_fallback() -> None:
    """Carrega variáveis de um arquivo .env se existir localmente."""
    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k and v and k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            logger.warning(f"Erro ao ler arquivo .env: {e}")


class SecretsManager:
    """Gerenciador de segredos do sistema JARVIS."""

    def __init__(self):
        _load_env_fallback()

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Recupera a chave de API para o provedor informado.
        Busca primeiramente no Windows Credential Manager (keyring),
        depois em variáveis de ambiente.
        """
        provider_clean = provider.strip().lower()
        key_name = f"api_key_{provider_clean}"

        # 1. Tentar via Keyring (Windows Credential Locker)
        try:
            import keyring
            secret = keyring.get_password(SERVICE_NAME, key_name)
            if secret and secret.strip():
                return secret.strip()
        except Exception as e:
            logger.debug(f"Keyring não acessível para {provider_clean}: {e}")

        # 2. Tentar via Variáveis de Ambiente (.env)
        env_var = PROVIDER_ENV_VARS.get(provider_clean)
        if env_var and env_var in os.environ:
            val = os.environ[env_var].strip()
            if val:
                return val

        # Também verificar formato genérico JARVIS_API_KEY_<PROVIDER>
        generic_var = f"JARVIS_API_KEY_{provider_clean.upper()}"
        if generic_var in os.environ:
            val = os.environ[generic_var].strip()
            if val:
                return val

        return None

    def set_api_key(self, provider: str, api_key: str) -> bool:
        """Salva a chave de API no Windows Credential Manager de forma segura."""
        provider_clean = provider.strip().lower()
        key_name = f"api_key_{provider_clean}"
        clean_key = api_key.strip()

        if not clean_key:
            return self.delete_api_key(provider)

        try:
            import keyring
            keyring.set_password(SERVICE_NAME, key_name, clean_key)
            logger.info(f"Chave de API salva com sucesso no Keyring para o provedor: {provider_clean}")
            return True
        except Exception as e:
            logger.error(f"Falha ao salvar chave de API no Keyring para {provider_clean}: {e}")
            # Salvar em os.environ como fallback de sessão
            env_var = PROVIDER_ENV_VARS.get(provider_clean, f"JARVIS_API_KEY_{provider_clean.upper()}")
            os.environ[env_var] = clean_key
            return False

    def delete_api_key(self, provider: str) -> bool:
        """Remove a chave de API do Windows Credential Manager."""
        provider_clean = provider.strip().lower()
        key_name = f"api_key_{provider_clean}"

        try:
            import keyring
            try:
                keyring.delete_password(SERVICE_NAME, key_name)
                logger.info(f"Chave de API removida do Keyring para {provider_clean}")
                return True
            except keyring.errors.PasswordDeleteError:
                return True  # Já não existia
        except Exception as e:
            logger.error(f"Erro ao remover chave de API do Keyring para {provider_clean}: {e}")
            return False

    def has_api_key(self, provider: str) -> bool:
        """Verifica se há chave configurada para o provedor."""
        key = self.get_api_key(provider)
        return bool(key and len(key) > 5)

    @staticmethod
    def mask_key(api_key: Optional[str]) -> str:
        """Retorna versão mascarada da chave para exibição segura (ex: sk-...1a2b)."""
        if not api_key:
            return "Não configurada"
        api_key = api_key.strip()
        if len(api_key) <= 8:
            return "********"
        return f"{api_key[:4]}...{api_key[-4:]}"


# Instância global do gerenciador de segredos
secrets_manager = SecretsManager()
