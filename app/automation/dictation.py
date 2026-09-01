"""
Modo Ditado Global Offline para o JARVIS.
Inspirado na funcionalidade de ditado privado do isair/jarvis (WisprFlow offline).
Transcreve fala localmente e cola/digita instantaneamente no aplicativo em foco.
"""

import time
import threading
import pyperclip
import pyautogui
from typing import Optional
from app.audio.stt import local_stt
from app.core.event_bus import event_bus, EventType
from app.core.logging_config import get_logger

logger = get_logger("automation.dictation")


class DictationManager:
    """Gerenciador de ditado contínuo e inserção de texto no aplicativo ativo."""

    def __init__(self):
        self._is_active = False
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        return self._is_active

    def toggle(self) -> bool:
        """Alterna o estado do modo ditado."""
        with self._lock:
            self._is_active = not self._is_active
            status = self._is_active
        logger.info(f"Modo Ditado {'ATIVADO' if status else 'DESATIVADO'}.")
        return status

    def start(self) -> None:
        with self._lock:
            self._is_active = True
        logger.info("Modo Ditado ativado.")

    def stop(self) -> None:
        with self._lock:
            self._is_active = False
        logger.info("Modo Ditado desativado.")

    def type_text_into_active_window(self, text: str) -> bool:
        """Copia o texto transcrito para a área de transferência e simula Ctrl+V na janela ativa."""
        clean_text = text.strip()
        if not clean_text:
            return False

        try:
            # Salva o conteúdo anterior do clipboard
            old_clip = ""
            try:
                old_clip = pyperclip.paste()
            except Exception:
                pass

            # Copia novo texto e insere
            pyperclip.copy(clean_text + " ")
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            logger.info(f"Texto ditado colado com sucesso na janela ativa: '{clean_text[:40]}...'")

            # Restaura clipboard original após pequeno intervalo
            def _restore():
                time.sleep(1.0)
                try:
                    if old_clip:
                        pyperclip.copy(old_clip)
                except Exception:
                    pass

            threading.Thread(target=_restore, daemon=True).start()
            return True

        except Exception as e:
            logger.error(f"Erro ao colar texto ditado na janela ativa: {e}")
            return False

    def process_dictation_audio(self, audio_data) -> Optional[str]:
        """Transcreve o áudio e cola diretamente no cursor da aplicação ativa."""
        text = local_stt.transcribe(audio_data)
        if text and text.strip():
            self.type_text_into_active_window(text)
            return text
        return None


dictation_manager = DictationManager()
