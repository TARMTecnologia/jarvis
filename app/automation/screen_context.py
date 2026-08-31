"""
Analise Visual e Contexto da Tela do Computador para o JARVIS.
Permite a IA visualizar a tela sob demanda do usuario.
"""

import io
import time
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ImageGrab
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("automation.screen_context")


class ScreenContextManager:
    """Gerencia captura segura de contexto de tela sob demanda."""

    @staticmethod
    def capture_screen_jpeg_bytes(quality: int = 75, max_dim: int = 1280) -> Tuple[Optional[bytes], str]:
        """
        Captura a tela inteira em memoria RAM, redimensiona e comprime em JPEG.
        Nenhum arquivo e salvo em disco.
        """
        try:
            img = ImageGrab.grab()
            orig_w, orig_h = img.size

            # Redimensiona se ultrapassar o limite para economizar tokens
            if orig_w > max_dim or orig_h > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=quality)
            jpeg_bytes = buf.getvalue()

            resolution_str = f"{orig_w}x{orig_h} (reduzido para {img.size[0]}x{img.size[1]})"
            logger.info(f"Contexto de tela capturado com sucesso: {resolution_str}")
            return jpeg_bytes, resolution_str

        except Exception as e:
            logger.error(f"Erro ao capturar contexto de tela: {e}")
            return None, str(e)


screen_context = ScreenContextManager()


@tool(
    name="get_screen_context",
    description="Captura a tela atual do computador para que a IA possa analisar e explicar o que esta acontecendo na tela.",
    permission_level=PermissionLevel.SAFE
)
def tool_get_screen_context() -> Dict[str, Any]:
    bytes_data, info = screen_context.capture_screen_jpeg_bytes()
    if bytes_data:
        return {
            "status": "success",
            "resolution": info,
            "message": "Captura de tela realizada. Analisando o conteudo da tela."
        }
    return {"status": "error", "error": info}
