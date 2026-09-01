"""
Ferramentas de Integracao e Envio de Mensagens no WhatsApp para o JARVIS.
Permite abrir conversas e redigir/enviar mensagens via WhatsApp Desktop e WhatsApp Web.
"""

import re
import urllib.parse
import webbrowser
import subprocess
from typing import Dict, Any, Optional
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.whatsapp")


def _format_phone(phone: str) -> str:
    """Limpa e formata o numero de telefone para o padrao internacional (E.164)."""
    digits = re.sub(r"\D", "", phone)
    # Se for numero brasileiro sem DDI 55 (ex: 11999999999 ou 21988888888)
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = "55" + digits
    return digits


@tool(
    name="send_whatsapp_message",
    description="Envia ou redige uma mensagem no WhatsApp para um contato ou número de telefone. Abre a conversa no WhatsApp Web / Desktop com o texto pronto.",
    permission_level=PermissionLevel.SAFE
)
def send_whatsapp_message(phone: str, message: str) -> Dict[str, Any]:
    """Envia uma mensagem para um numero no WhatsApp."""
    clean_phone = _format_phone(phone)
    if not clean_phone or len(clean_phone) < 8:
        return {"status": "error", "error": f"Número de telefone inválido: '{phone}'."}

    encoded_msg = urllib.parse.quote(message)
    whatsapp_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}"

    try:
        webbrowser.open(whatsapp_url)
        logger.info(f"WhatsApp aberto para o número {clean_phone} com mensagem preparada.")
        return {
            "status": "success",
            "phone": clean_phone,
            "message_sent": message,
            "info": f"WhatsApp aberto para {clean_phone}. Mensagem carregada na conversa: '{message}'."
        }
    except Exception as e:
        logger.error(f"Erro ao abrir WhatsApp: {e}")
        return {"status": "error", "error": f"Falha ao abrir WhatsApp: {str(e)}"}


@tool(
    name="open_whatsapp",
    description="Abre o WhatsApp Web ou o aplicativo do WhatsApp no computador.",
    permission_level=PermissionLevel.SAFE
)
def open_whatsapp() -> Dict[str, Any]:
    """Abre o WhatsApp no computador."""
    try:
        webbrowser.open("https://web.whatsapp.com")
        logger.info("WhatsApp aberto com sucesso.")
        return {"status": "success", "message": "WhatsApp aberto no navegador."}
    except Exception as e:
        logger.error(f"Erro ao abrir WhatsApp: {e}")
        return {"status": "error", "error": f"Falha ao abrir WhatsApp: {str(e)}"}
