"""
Controle e Automacao Segura de Mouse e Teclado para o JARVIS.
Fica desativado por padrao e requer autorizacao explicita.
"""

import time
from typing import Dict, Any, Optional
import pyautogui
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("automation.controller")

# Margem de seguranca para abortar se o mouse for puxado para o canto da tela
pyautogui.FAILSAFE = True


@tool(
    name="click_screen",
    description="Clica com o mouse nas coordenadas (x, y) da tela. Requer que a automacao de computador esteja ativada.",
    permission_level=PermissionLevel.SENSITIVE
)
def click_screen(x: int, y: int, clicks: int = 1, button: str = "left") -> Dict[str, Any]:
    if not app_config.system.allow_computer_automation:
        return {
            "status": "denied",
            "error": "A automacao de mouse e teclado esta desativada nas configuracoes do JARVIS por motivos de seguranca."
        }

    try:
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return {"status": "success", "message": f"Clique ({button}) executado em ({x}, {y})."}
    except Exception as e:
        logger.error(f"Erro ao clicar na tela: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="type_text",
    description="Digita um texto no campo ativo do teclado. Requer que a automacao de computador esteja ativada.",
    permission_level=PermissionLevel.SENSITIVE
)
def type_text(text: str) -> Dict[str, Any]:
    if not app_config.system.allow_computer_automation:
        return {
            "status": "denied",
            "error": "A automacao de teclado esta desativada nas configuracoes do JARVIS."
        }

    try:
        pyautogui.write(text, interval=0.02)
        return {"status": "success", "message": f"Texto digitado ({len(text)} caracteres)."}
    except Exception as e:
        logger.error(f"Erro ao digitar texto: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="press_key",
    description="Pressiona uma tecla especial (ex: 'enter', 'esc', 'tab', 'space', 'backspace'). Requer automacao ativada.",
    permission_level=PermissionLevel.SENSITIVE
)
def press_key(key_name: str) -> Dict[str, Any]:
    if not app_config.system.allow_computer_automation:
        return {
            "status": "denied",
            "error": "A automacao de computador esta desativada nas configuracoes."
        }

    try:
        pyautogui.press(key_name.lower())
        return {"status": "success", "message": f"Tecla '{key_name}' pressionada."}
    except Exception as e:
        logger.error(f"Erro ao pressionar tecla {key_name}: {e}")
        return {"status": "error", "error": str(e)}
