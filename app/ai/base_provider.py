"""
Interface Abstrata AIProvider e DTOs de Comunicação.
Garante desacoplamento total entre o JARVIS e os SDKs de IA.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
import json
from app.core.logging_config import get_logger

logger = get_logger("ai.base_provider")


@dataclass
class ToolCallRequest:
    """Solicitação de execução de ferramenta emitida pelo modelo."""
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponseChunk:
    """Fragmento de resposta em streaming."""
    text: str = ""
    is_done: bool = False
    tool_calls: Optional[List[ToolCallRequest]] = None
    finish_reason: Optional[str] = None


@dataclass
class AIResponse:
    """Resposta consolidada de um provedor de IA."""
    text: str
    audio_data: Optional[bytes] = None
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    raw_response: Optional[Any] = None


class AIProvider(ABC):
    """Classe base abstrata para todos os provedores de inteligência artificial."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or ""
        self.model = model or ""
        self._is_initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """Inicializa o cliente SDK com as credenciais configuradas."""
        pass

    @abstractmethod
    async def test_connection(self) -> Tuple[bool, str]:
        """Testa a validade da API Key e a conectividade com o serviço."""
        pass

    @abstractmethod
    async def send_message(
        self,
        prompt: str,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AIResponse:
        """Envia mensagem síncrona/esperada para o modelo."""
        pass

    @abstractmethod
    async def stream_response(
        self,
        prompt: str,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[AIResponseChunk, None]:
        """Gera streaming de resposta de texto e eventuais tool calls."""
        pass

    @abstractmethod
    def supports_realtime(self) -> bool:
        """Indica se o provedor possui suporte a conexão WebSocket de baixa latência."""
        pass

    @abstractmethod
    def supports_vision(self) -> bool:
        """Indica se o modelo suporta processamento multimodal de imagens."""
        pass

    @abstractmethod
    def supports_native_audio(self) -> bool:
        """Indica se o modelo gera áudio nativo na resposta."""
        pass

    @abstractmethod
    def format_tools(self, tools: List[Dict[str, Any]]) -> Any:
        """Converte as ferramentas do formato interno padrão para o formato específico da API."""
        pass

    @staticmethod
    def parse_tool_arguments(raw_args: Any) -> Dict[str, Any]:
        """Converte argumentos em formato string/dict para dict Python de forma resiliente."""
        if isinstance(raw_args, dict):
            return raw_args
        if isinstance(raw_args, str):
            try:
                return json.loads(raw_args)
            except Exception:
                return {}
        return {}
