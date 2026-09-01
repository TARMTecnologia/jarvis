"""
Provedor de IA Ollama / LM Studio Local para o JARVIS.
Permite executar modelos 100% locais e offline (Llama 3, Qwen 2.5, DeepSeek, Mistral, Gemma).
"""

import json
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from app.ai.base_provider import AIProvider, AIResponse, AIResponseChunk, ToolCallRequest
from app.core.logging_config import get_logger

logger = get_logger("ai.ollama")

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "llama3.2:latest"


class OllamaProvider(AIProvider):
    """Provedor para servidores locais compatíveis com API OpenAI (Ollama, LM Studio, LocalAI)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(api_key=api_key or "ollama", model=model or DEFAULT_OLLAMA_MODEL)
        self.base_url = base_url or DEFAULT_OLLAMA_BASE_URL
        self._async_client = None
        self.initialize()

    def initialize(self) -> bool:
        """Inicializa o cliente assíncrono apontando para o servidor local."""
        try:
            from openai import AsyncOpenAI
            self._async_client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "ollama"
            )
            self._is_initialized = True
            logger.info(f"OllamaProvider inicializado em {self.base_url} com modelo '{self.model}'.")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar OllamaProvider: {e}")
            self._is_initialized = False
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        """Verifica se o servidor Ollama/LM Studio local está ativo."""
        try:
            from openai import AsyncOpenAI
            client = self._async_client or AsyncOpenAI(base_url=self.base_url, api_key="ollama")
            models = await client.models.list()
            if models and models.data:
                names = [m.id for m in models.data]
                return True, f"Servidor Local OK! ({len(names)} modelos encontrados: {', '.join(names[:3])})"
            return True, "Servidor Local conectado com sucesso."
        except Exception as e:
            return False, f"Servidor local offline ({self.base_url}). Certifique-se de que o Ollama ou LM Studio está aberto."

    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
            })
        return openai_tools

    def _build_messages(
        self,
        prompt: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            for turn in history:
                role = turn.get("role", "user")
                if role in ("user", "system"):
                    messages.append({"role": role, "content": str(turn.get("content", ""))})
                elif role == "assistant":
                    msg_item: Dict[str, Any] = {"role": "assistant", "content": turn.get("content") or None}
                    if "tool_calls" in turn and turn["tool_calls"]:
                        msg_item["tool_calls"] = turn["tool_calls"]
                    messages.append(msg_item)
                elif role == "tool":
                    messages.append({
                        "role": "tool",
                        "tool_call_id": turn.get("tool_call_id", ""),
                        "content": str(turn.get("content", ""))
                    })

        if prompt and prompt.strip():
            messages.append({"role": "user", "content": prompt.strip()})

        return messages

    async def send_message(
        self,
        prompt: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AIResponse:
        """Envia requisição para o LLM local."""
        if not self._is_initialized and not self.initialize():
            return AIResponse(text=f"Erro: Não foi possível conectar ao servidor Ollama em {self.base_url}.")

        messages = self._build_messages(prompt, images, history, system_prompt)
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        if tools and len(tools) > 0:
            kwargs["tools"] = self.format_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            completion = await self._async_client.chat.completions.create(**kwargs)
            choice = completion.choices[0]
            message = choice.message

            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    args = self.parse_tool_arguments(tc.function.arguments)
                    tool_calls.append(ToolCallRequest(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args
                    ))

            return AIResponse(
                text=message.content or "",
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason or "stop",
                raw_response=completion
            )
        except Exception as e:
            logger.error(f"Erro ao consultar Ollama local: {e}")
            return AIResponse(text=f"Desculpe, ocorreu um erro com o modelo local Ollama: {str(e)}")

    async def stream_response(
        self,
        prompt: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[AIResponseChunk, None]:
        if not self._is_initialized and not self.initialize():
            yield AIResponseChunk(text="Erro: Ollama local não inicializado.", is_done=True)
            return

        try:
            messages = self._build_messages(prompt, images, history, system_prompt)
            stream = await self._async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield AIResponseChunk(text=chunk.choices[0].delta.content, is_done=False)
            yield AIResponseChunk(text="", is_done=True)
        except Exception as e:
            yield AIResponseChunk(text=f"\n[Erro no streaming local: {e}]", is_done=True)

    def supports_realtime(self) -> bool:
        return False

    def supports_vision(self) -> bool:
        return "vision" in self.model.lower() or "llava" in self.model.lower()

    def supports_native_audio(self) -> bool:
        return False
