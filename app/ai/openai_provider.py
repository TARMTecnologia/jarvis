"""
Provedor de Inteligencia Artificial para a OpenAI (GPT-4o, GPT-4o-mini e o1).
Suporte a Tool Calling nativo, Visao Multimodal em Alta Definicao, Streaming e mensagens estritamente tipadas.
"""

import os
import json
import base64
import asyncio
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from app.ai.base_provider import AIProvider, AIResponse, ToolCallRequest, ToolCall, AIResponseChunk
from app.core.config import app_config
from app.security.secrets import secrets_manager
from app.core.logging_config import get_logger

logger = get_logger("ai.openai")

FALLBACK_MODEL_MAP = {
    "gpt-4-vision-preview": "gpt-4o",
    "gpt-4-turbo-preview": "gpt-4o",
    "gpt-4-turbo": "gpt-4o",
    "gpt-3.5-turbo": "gpt-4o-mini",
    "gpt-3.5-turbo-16k": "gpt-4o-mini",
    "gpt-4": "gpt-4o"
}


class OpenAIProvider(AIProvider):
    """Integracao robusta com a API da OpenAI."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key or secrets_manager.get_api_key("openai"), model=model or app_config.ai.model or "gpt-4o-mini")
        self._client = None
        self._is_initialized = False

    def initialize(self) -> bool:
        """Inicializa o cliente da OpenAI validando a chave de API."""
        if not self.api_key:
            self.api_key = secrets_manager.get_api_key("openai")
        if not self.api_key:
            logger.warning("Chave da OpenAI nao encontrada em secrets.json.")
            self._is_initialized = False
            return False

        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
            self._is_initialized = True
            logger.info(f"Provedor OpenAI inicializado com o modelo: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar AsyncOpenAI: {e}")
            self._is_initialized = False
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        """Testa a validade da API Key e conectividade."""
        if not self.api_key:
            self.api_key = secrets_manager.get_api_key("openai")
        if not self.api_key:
            return False, "API Key da OpenAI não encontrada."

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, timeout=5.0)
            client.models.list()
            return True, "Conexão com a OpenAI estabelecida com sucesso."
        except Exception as e:
            return False, f"Falha na conexão com a OpenAI: {str(e)}"

    def supports_realtime(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return True

    def supports_native_audio(self) -> bool:
        return False

    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formata as definicoes de ferramentas no formato padrao OpenAI Tools."""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {
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
        """Constroi o payload de mensagens com suporte oficial a tool_calls e strings validas."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": str(system_prompt)})

        if history:
            for turn in history:
                role = turn.get("role", "user")
                if role == "assistant":
                    content_val = turn.get("content")
                    msg_item: Dict[str, Any] = {
                        "role": "assistant",
                        "content": str(content_val) if content_val is not None else ""
                    }
                    if "tool_calls" in turn and turn["tool_calls"]:
                        formatted_tcs = []
                        for tc in turn["tool_calls"]:
                            if isinstance(tc, dict):
                                tc_id = tc.get("id", "")
                                if "function" in tc:
                                    func_name = tc["function"].get("name", "")
                                    func_args = tc["function"].get("arguments", "{}")
                                else:
                                    func_name = tc.get("name", "")
                                    func_args = tc.get("arguments", "{}")
                                if isinstance(func_args, dict):
                                    func_args = json.dumps(func_args)
                                formatted_tcs.append({
                                    "id": tc_id,
                                    "type": "function",
                                    "function": {
                                        "name": func_name,
                                        "arguments": str(func_args)
                                    }
                                })
                        if formatted_tcs:
                            msg_item["tool_calls"] = formatted_tcs
                    messages.append(msg_item)

                elif role == "tool":
                    messages.append({
                        "role": "tool",
                        "tool_call_id": turn.get("tool_call_id", ""),
                        "content": str(turn.get("content", ""))
                    })

                elif role in ("user", "system"):
                    messages.append({"role": role, "content": str(turn.get("content", ""))})

        if prompt and prompt.strip():
            if images and len(images) > 0:
                content_list: List[Dict[str, Any]] = [{"type": "text", "text": prompt.strip()}]
                for img_bytes in images:
                    b64_img = base64.b64encode(img_bytes).decode("utf-8")
                    content_list.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_img}",
                            "detail": "high"
                        }
                    })
                messages.append({"role": "user", "content": content_list})
            else:
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
        """Envia mensagem assincrona para a OpenAI com recuperacao automatica em caso de modelo 404."""
        if not self._is_initialized and not self.initialize():
            return AIResponse(text="Erro: Provedor OpenAI nao esta inicializado com uma chave valida. Cadastre sua API Key nas Configuracoes.")

        messages = self._build_messages(prompt, images, history, system_prompt)
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        if tools and len(tools) > 0:
            kwargs["tools"] = self.format_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            return await self._execute_chat_completion(kwargs)
        except Exception as e:
            err_str = str(e)
            logger.error(f"Erro na chamada OpenAI: {err_str}")

            if "404" in err_str or "model_not_found" in err_str or "does not exist" in err_str:
                fallback = FALLBACK_MODEL_MAP.get(self.model, "gpt-4o")
                if fallback != self.model:
                    logger.warning(f"Modelo '{self.model}' gerou 404. Tentando fallback automatico para '{fallback}'...")
                    self.model = fallback
                    kwargs["model"] = fallback
                    try:
                        return await self._execute_chat_completion(kwargs)
                    except Exception as e2:
                        logger.error(f"Erro tambem no fallback da OpenAI: {e2}")
                        return AIResponse(text=f"Erro ao comunicar com a OpenAI apos fallback: {e2}")

            return AIResponse(text=f"Desculpe, ocorreu um erro ao comunicar com a OpenAI: {err_str}")

    async def _execute_chat_completion(self, kwargs: Dict[str, Any]) -> AIResponse:
        """Executa a requisicao assincrona e converte a resposta para AIResponse."""
        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {"raw_arguments": tc.function.arguments}

                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args
                ))

        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        return AIResponse(
            text=message.content or "",
            tool_calls=tool_calls if tool_calls else [],
            usage={"input_tokens": input_tokens, "output_tokens": output_tokens}
        )

    async def stream_response(
        self,
        prompt: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[AIResponseChunk, None]:
        """Gera streaming de resposta de texto."""
        if not self._is_initialized and not self.initialize():
            yield AIResponseChunk(text="Erro de autenticação com OpenAI.", is_done=True)
            return

        messages = self._build_messages(prompt, images, history, system_prompt)
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        if tools and len(tools) > 0:
            kwargs["tools"] = self.format_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.content or ""
                finish_reason = chunk.choices[0].finish_reason
                yield AIResponseChunk(text=content, is_done=(finish_reason is not None), finish_reason=finish_reason)
        except Exception as e:
            logger.error(f"Erro no streaming OpenAI: {e}")
            yield AIResponseChunk(text=f"Erro de streaming: {e}", is_done=True)
