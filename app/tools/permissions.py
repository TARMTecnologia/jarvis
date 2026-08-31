"""
Sistema de Gerenciamento de Permissoes e Seguranca para Execucao de Ferramentas.
Classifica ferramentas em SAFE, SENSITIVE e DESTRUCTIVE com fluxo de confirmacao.
"""

from enum import Enum
from typing import Dict, Any, Optional, Callable, Tuple
from app.core.logging_config import get_logger

logger = get_logger("tools.permissions")


class PermissionLevel(str, Enum):
    """Niveis de seguranca para execucao de ferramentas locais."""
    SAFE = "SAFE"                 # Leitura e operacoes inofensivas (CPU, relogio, abrir app/url)
    SENSITIVE = "SENSITIVE"       # Alteracoes no sistema (fechar app, criar arquivos, clipboard)
    DESTRUCTIVE = "DESTRUCTIVE"   # Acoes criticas (apagar arquivos, desligar/reiniciar SO)


class PermissionManager:
    """Validador e gerenciador de permissoes de ferramentas."""

    def __init__(self):
        self._confirmation_handler: Optional[Callable[[str, str, Dict[str, Any]], bool]] = None
        self._auto_confirm_safe: bool = True

    def set_confirmation_handler(self, handler: Callable[[str, str, Dict[str, Any]], bool]) -> None:
        """Registra o manipulador de dialogo de confirmacao da UI."""
        self._confirmation_handler = handler

    def requires_confirmation(self, level: PermissionLevel) -> bool:
        """Indica se o nivel de permissao exige confirmacao previa do usuario."""
        return level in (PermissionLevel.SENSITIVE, PermissionLevel.DESTRUCTIVE)

    def check_permission(self, tool_name: str, level: PermissionLevel, args: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verifica se a ferramenta pode ser executada.
        Para acoes destrutivas/sensiveis, aciona a confirmacao do usuario.
        """
        if level == PermissionLevel.SAFE and self._auto_confirm_safe:
            return True, "Operacao segura autorizada automaticamente."

        if self.requires_confirmation(level):
            logger.warning(f"Ferramenta '{tool_name}' com nivel {level.value} requer confirmacao.")
            
            if self._confirmation_handler is not None:
                try:
                    confirmed = self._confirmation_handler(tool_name, level.value, args)
                    if confirmed:
                        return True, "Acao confirmada pelo usuario."
                    else:
                        return False, "Acao cancelada pelo usuario."
                except Exception as e:
                    logger.error(f"Erro ao solicitar confirmacao de permissao: {e}")
                    return False, f"Falha na confirmacao de seguranca: {e}"
            else:
                if level == PermissionLevel.DESTRUCTIVE:
                    return False, f"Acao destrutiva '{tool_name}' bloqueada: requer confirmacao interativa."
                return True, "Acao sensivel executada sem handler de confirmacao."

        return True, "Autorizado."


# Instancia global compartilhada
permission_manager = PermissionManager()
