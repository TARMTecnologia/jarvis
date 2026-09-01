"""
Modulo de Ferramentas e Integracao com o Sistema Operacional do JARVIS.
Importa e registra todas as ferramentas automaticamente.
"""

from app.tools.registry import tool_registry, tool
from app.tools.permissions import permission_manager, PermissionLevel
from app.tools.executor import tool_executor

# Importa os modulos de ferramentas para registrar no catalogo
import app.tools.system_tools
import app.tools.browser_tools
import app.tools.weather_tools
import app.tools.whatsapp_tools
import app.tools.file_tools
import app.tools.clipboard_tools
import app.tools.screenshot_tools
import app.tools.note_tools
import app.tools.reminder_tools

__all__ = [
    "tool_registry",
    "tool",
    "permission_manager",
    "PermissionLevel",
    "tool_executor"
]
