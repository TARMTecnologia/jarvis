"""
Provedor de IA Ollama / LM Studio Local para o JARVIS.
Suporta modelos locais como DeepSeek-R1 (com filtro de tags <think>), Llama 3.2, Qwen 2.5, Mistral e Gemma.
"""

import re
import json
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from app.ai.base_provider import AIProvider, AIResponse, AIResponseChunk, ToolCallRequest
from app.core.logging_config import get_logger

logger = get_logger("ai.ollama")

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "deepseek-r1:8b"


class OllamaProvider(AIProvider):
    """Provedor resiliente para servidores locais compatíveis com API OpenAI (Ollama, LM Studio)."""

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
        """Verifica se o servidor Ollama/LM Studio local está ativo e lista modelos."""
        try:
            from openai import AsyncOpenAI
            client = self._async_client or AsyncOpenAI(base_url=self.base_url, api_key="ollama")
            models = await client.models.list()
            if models and models.data:
                names = [m.id for m in models.data]
                return True, f"Ollama Local Conectado! ({len(names)} modelos encontrados: {', '.join(names[:4])})"
            return True, "Servidor Local conectado com sucesso."
        except Exception as e:
            return False, f"Ollama local offline ({self.base_url}). Certifique-se de que o Ollama está aberto."

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

    def _clean_deepseek_reasoning(self, text: Optional[str]) -> str:
        """Remove tags internas <think>...</think> do DeepSeek-R1 para resposta limpa e falada."""
        if not text:
            return ""
        # Remove bloco <think>...</think>
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
        # Remove tag <think> aberta se nao fechou
        cleaned = re.sub(r"^<think>[\s\S]*$", "", cleaned).strip()
        return cleaned if cleaned else text.strip()

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
        """Envia requisição para o LLM local com suporte a DeepSeek-R1 e fallback seguro de ferramentas."""
        if not self._is_initialized and not self.initialize():
            return AIResponse(text=f"Erro: Não foi possível conectar ao servidor Ollama em {self.base_url}.")

        messages = self._build_messages(prompt, images, history, system_prompt)
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        # Modelos como deepseek-r1 não suportam schema de tools nativo no Ollama
        is_reasoning_model = any(k in self.model.lower() for k in ["deepseek", "r1", "think"])
        if tools and len(tools) > 0 and not is_reasoning_model:
            kwargs["tools"] = self.format_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            return await self._execute(kwargs)
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Erro na requisição Ollama ({err_str}). Tentando sem tools...")
            if "tools" in kwargs:
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                try:
                    return await self._execute(kwargs)
                except Exception as e2:
                    return AIResponse(text=f"Erro no modelo local Ollama '{self.model}': {str(e2)}")
            return AIResponse(text=f"Erro no modelo local Ollama '{self.model}': {err_str}")

    async def _execute(self, kwargs: Dict[str, Any]) -> AIResponse:
        completion = await self._async_client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        message = choice.message

        raw_content = message.content or ""
        clean_content = self._clean_deepseek_reasoning(raw_content)

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
            text=clean_content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            raw_response=completion
        )

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
            inside_think = False
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    if "<think>" in token:
                        inside_think = True
                        continue
                    if "</think>" in token:
                        inside_think = False
                        continue
                    if not inside_think:
                        yield AIResponseChunk(text=token, is_done=False)
            yield AIResponseChunk(text="", is_done=True)
        except Exception as e:
            yield AIResponseChunk(text=f"\n[Erro no streaming Ollama: {e}]", is_done=True)

    def supports_realtime(self) -> bool:
        return False

    def supports_vision(self) -> bool:
        return any(v in self.model.lower() for v in ["vision", "llava", "minicpm", "bakllava"])

    def supports_native_audio(self) -> bool:
        return False
