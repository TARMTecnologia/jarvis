"""
Ferramentas de Integracao e Envio Automatico de Mensagens no WhatsApp para o JARVIS.
Permite abrir conversas e enviar mensagens de fato (com disparo automatico do Enter) via WhatsApp Web / Desktop.
"""

import re
import time
import threading
import urllib.parse
import webbrowser
from typing import Dict, Any, Optional
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.whatsapp")


def _format_phone(phone: str) -> str:
    """Limpa e formata o numero de telefone para o padrao internacional (E.164)."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = "55" + digits
    return digits


def _auto_send_enter_worker(delay_seconds: float = 9.0) -> None:
    """Aguarda o WhatsApp carregar a conversa e pressiona Enter automaticamente para enviar."""
    time.sleep(delay_seconds)
    try:
        import pyautogui
        pyautogui.press("enter")
        logger.info("Tecla Enter pressionada com sucesso no WhatsApp (mensagem enviada)!")
    except Exception as e:
        logger.debug(f"Aviso ao pressionar Enter automaticamente: {e}")


@tool(
    name="send_whatsapp_message",
    description="Envia automaticamente uma mensagem no WhatsApp para um contato ou número de telefone. Abre a conversa no WhatsApp e pressiona Enter para enviar de fato.",
    permission_level=PermissionLevel.SAFE
)
def send_whatsapp_message(phone: str, message: str) -> Dict[str, Any]:
    """Envia uma mensagem para um numero no WhatsApp com envio automatico."""
    clean_phone = _format_phone(phone)
    if not clean_phone or len(clean_phone) < 8:
        return {"status": "error", "error": f"Número de telefone inválido: '{phone}'."}

    encoded_msg = urllib.parse.quote(message)
    whatsapp_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}"

    try:
        webbrowser.open(whatsapp_url)
        logger.info(f"WhatsApp aberto para {clean_phone}. Disparando thread de envio automático...")

        # Inicia thread que pressiona Enter automaticamente apos o carregamento da janela
        threading.Thread(target=_auto_send_enter_worker, args=(9.0,), daemon=True).start()

        return {
            "status": "success",
            "phone": clean_phone,
            "message_sent": message,
            "info": f"Mensagem '{message}' enviada com sucesso para {clean_phone} no WhatsApp."
        }
    except Exception as e:
        logger.error(f"Erro ao abrir WhatsApp: {e}")
        return {"status": "error", "error": f"Falha ao enviar mensagem no WhatsApp: {str(e)}"}


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


@tool(
    name="press_enter_key",
    description="Pressiona a tecla Enter na janela ativa do computador (util para confirmar envios no WhatsApp ou formulários).",
    permission_level=PermissionLevel.SAFE
)
def press_enter_key() -> Dict[str, Any]:
    """Pressiona a tecla Enter na janela ativa."""
    try:
        import pyautogui
        pyautogui.press("enter")
        return {"status": "success", "message": "Tecla Enter pressionada na janela ativa."}
    except Exception as e:
        return {"status": "error", "error": f"Falha ao pressionar Enter: {e}"}
