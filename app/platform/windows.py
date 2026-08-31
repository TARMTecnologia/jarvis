"""
Integracao Especifica com o Windows 10/11 para o JARVIS.
Gerencia Registro de Inicializacao com o Windows, Notificacoes e Agendador de Lembretes.
"""

import os
import sys
import time
import winreg
import threading
import subprocess
from typing import Optional, List, Dict, Any, Callable
from app.platform.base import BasePlatform
from app.memory.database import db
from app.core.event_bus import event_bus, EventType
from app.core.logging_config import get_logger

logger = get_logger("platform.windows")

RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "JARVIS_Assistant"


class WindowsPlatform(BasePlatform):
    """Implementacao de integracao nativa com o Windows 10 e 11."""

    def __init__(self):
        self._tray_notification_callback: Optional[Callable[[str, str], None]] = None

    def set_tray_callback(self, callback: Callable[[str, str], None]) -> None:
        """Registra o callback da System Tray para exibicao de baloes de notificacao."""
        self._tray_notification_callback = callback

    def show_notification(self, title: str, message: str) -> bool:
        """Exibe notificacao nativa no Windows."""
        try:
            # 1. Tenta via callback da Tray do PySide6 se a interface estiver rodando
            if self._tray_notification_callback is not None:
                self._tray_notification_callback(title, message)
                return True

            # 2. Fallback via script PowerShell nativo do Windows (sem dependências extras)
            ps_script = f"""
            [reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null
            $notify = new-object system.windows.forms.notifyicon
            $notify.icon = [system.drawing.systemicons]::information
            $notify.visible = $true
            $notify.showballoontip(5000, '{title}', '{message}', [system.windows.forms.tooltipicon]::info)
            Start-Sleep -s 1
            $notify.dispose()
            """
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_script], shell=False)
            return True
        except Exception as e:
            logger.error(f"Erro ao disparar notificacao Windows: {e}")
            return False

    def set_startup_with_windows(self, enable: bool) -> bool:
        """Adiciona ou remove o JARVIS da chave de inicialização no Registro do Windows do usuário atual."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE)
            if enable:
                # Caminho para o executavel ou python script
                if getattr(sys, "frozen", False):
                    exe_path = f'"{sys.executable}"'
                else:
                    python_exe = sys.executable
                    main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
                    exe_path = f'"{python_exe}" "{main_script}"'

                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
                logger.info("JARVIS configurado para iniciar automaticamente com o Windows.")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Inicializacao com o Windows desativada.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logger.error(f"Erro ao modificar Registro do Windows (Run key): {e}")
            return False

    def is_startup_enabled(self) -> bool:
        """Verifica se o JARVIS está cadastrado para iniciar com o Windows."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, OSError):
            return False


class ReminderScheduler:
    """Thread em segundo plano que monitora e dispara lembretes agendados no SQLite."""

    def __init__(self, platform: WindowsPlatform, check_interval_seconds: float = 10.0):
        self.platform = platform
        self.check_interval = check_interval_seconds
        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Inicia o monitoramento de lembretes."""
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Agendador de lembretes iniciado.")

    def stop(self) -> None:
        """Para o monitoramento de lembretes."""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Agendador de lembretes parado.")

    def _scheduler_loop(self) -> None:
        while self._is_running:
            try:
                now_ts = time.time()
                conn = db.get_connection()
                
                # Busca lembretes cujo horario ja chegou e ainda nao foram marcados como concluidos
                cursor = conn.execute("""
                    SELECT id, text, due_timestamp
                    FROM reminders
                    WHERE is_completed = 0 AND due_timestamp <= ?
                """, (now_ts,))
                
                due_reminders = cursor.fetchall()
                
                for row in due_reminders:
                    rem_id = row["id"]
                    rem_text = row["text"]

                    logger.info(f"Disparando lembrete agendado: '{rem_text}'")

                    # Marca como concluido no banco
                    with conn:
                        conn.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (rem_id,))

                    # Exibe notificacao nativa
                    self.platform.show_notification(
                        title="JARVIS — Lembrete",
                        message=rem_text
                    )

                    # Publica evento para a UI e audio falado
                    event_bus.publish(
                        EventType.REMINDER_TRIGGERED,
                        {"id": rem_id, "text": rem_text}
                    )

            except Exception as e:
                logger.error(f"Erro no loop do agendador de lembretes: {e}")

            time.sleep(self.check_interval)


windows_platform = WindowsPlatform()
reminder_scheduler = ReminderScheduler(platform=windows_platform)
