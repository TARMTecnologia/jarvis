"""
Ferramentas de Captura de Tela (Screenshot) para o JARVIS.
"""

import os
import io
import time
from pathlib import Path
from typing import Dict, Any
from PIL import ImageGrab
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.screenshot")


@tool(
    name="take_screenshot",
    description="Captura um print da tela inteira do computador. Se save_to_desktop for True, salva como PNG na Area de Trabalho.",
    permission_level=PermissionLevel.SAFE
)
def take_screenshot(save_to_desktop: bool = True) -> Dict[str, Any]:
    try:
        screenshot = ImageGrab.grab()
        width, height = screenshot.size
        
        saved_path = None
        if save_to_desktop:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_jarvis_{timestamp_str}.png"
            desktop_path = Path.home() / "Desktop" / filename
            screenshot.save(desktop_path, format="PNG")
            saved_path = str(desktop_path)
            logger.info(f"Screenshot salvo na Area de Trabalho: {saved_path}")

        return {
            "status": "success",
            "resolution": f"{width}x{height}",
            "saved_to_desktop": save_to_desktop,
            "file_path": saved_path,
            "message": f"Print da tela capturado com sucesso ({width}x{height})." + (f" Salvo em: {saved_path}" if saved_path else "")
        }
    except Exception as e:
        logger.error(f"Erro ao capturar tela: {e}")
        return {"status": "error", "error": str(e)}
