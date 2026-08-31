"""
Ferramentas de Area de Transferencia (Clipboard) para o JARVIS.
"""

import pyperclip
from typing import Dict, Any
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.clipboard")


@tool(
    name="read_clipboard",
    description="Le o texto copiado atualmente na area de transferencia do computador.",
    permission_level=PermissionLevel.SAFE
)
def read_clipboard() -> Dict[str, Any]:
    try:
        content = pyperclip.paste()
        if not content:
            return {"status": "empty", "content": "", "message": "A area de transferencia esta vazia."}
        
        truncated = content[:2000]
        return {
            "status": "success",
            "content": truncated,
            "length": len(content),
            "is_truncated": len(content) > 2000
        }
    except Exception as e:
        logger.error(f"Erro ao ler clipboard: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="write_clipboard",
    description="Copia um texto informado para a area de transferencia do usuario.",
    permission_level=PermissionLevel.SAFE
)
def write_clipboard(text: str) -> Dict[str, Any]:
    try:
        pyperclip.copy(text)
        return {
            "status": "success",
            "message": "Texto copiado para a area de transferencia.",
            "copied_length": len(text)
        }
    except Exception as e:
        logger.error(f"Erro ao escrever no clipboard: {e}")
        return {"status": "error", "error": str(e)}
