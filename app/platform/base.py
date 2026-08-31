"""
Interface Abstrata de Plataforma para o JARVIS.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BasePlatform(ABC):
    """Classe base para integracao com o sistema operacional."""

    @abstractmethod
    def show_notification(self, title: str, message: str) -> bool:
        """Exibe uma notificacao nativa do sistema operacional."""
        pass

    @abstractmethod
    def set_startup_with_windows(self, enable: bool) -> bool:
        """Configura a inicializacao automatica com o sistema."""
        pass

    @abstractmethod
    def is_startup_enabled(self) -> bool:
        """Verifica se a inicializacao automatica esta ativa."""
        pass
