"""
Ponto de Entrada Principal do Aplicativo JARVIS Desktop.
Inicializa o logging, thread de background asyncio, QApplication e abre a MainWindow.
"""

import sys
import os
import asyncio
import threading
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from app.core.logging_config import setup_logging, get_logger
from app.core.config import app_config
from app.core.orchestrator import orchestrator
from app.ui.main_window import MainWindow
from app.ui.setup_wizard import SetupWizard

# Inicializa sistema de logging seguro
setup_logging()
logger = get_logger("main")


def start_asyncio_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Roda o event loop asyncio em uma thread dedicada de background para nao bloquear a interface Qt."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def main() -> None:
    """Funcao principal de execucao do JARVIS."""
    logger.info("Iniciando JARVIS Assistente Desktop...")

    # Cria aplicacao Qt
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    app.setOrganizationName("JARVIS_AI")
    app.setQuitOnLastWindowClosed(False)  # Permite continuar ativo na Tray

    # Cria e inicia loop asyncio em thread separada
    bg_loop = asyncio.new_event_loop()
    orchestrator._loop = bg_loop
    bg_thread = threading.Thread(target=start_asyncio_background_loop, args=(bg_loop,), daemon=True)
    bg_thread.start()

    # Inicializa orquestrador e subsistemas
    orchestrator.initialize()

    # Se for a primeira execucao (e nao tiver sido configurado ainda), exibe o Setup Wizard
    if not app_config.system.first_run_completed:
        logger.info("Primeira execucao detectada. Abrindo Assistente de Configuracao (Setup Wizard)...")
        wizard = SetupWizard()
        wizard.exec()
        app_config.system.first_run_completed = True
        app_config.save()
        logger.info("Setup Wizard finalizado e configuracoes salvas.")
        orchestrator.reload_provider()

    # Exibe a Janela Principal com o Avatar Robótico
    main_window = MainWindow()
    main_window.show()

    # Executa loop de eventos da UI
    exit_code = app.exec()

    # Encerra loop de background e subsistemas
    orchestrator.shutdown()
    bg_loop.call_soon_threadsafe(bg_loop.stop)
    logger.info(f"JARVIS finalizado com codigo {exit_code}.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
