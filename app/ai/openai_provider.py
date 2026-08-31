"""
Provedor de IA OpenAI para o JARVIS.
Suporta modelos GPT-4o, GPT-4o-mini, o3-mini, o1, visão multimodal e function calling com formatação estrita de tool_calls.
"""

import base64
import json
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from app.ai.base_provider import AIProvider, AIResponse, AIResponseChunk, ToolCallRequest
from app.core.logging_config import get_logger

logger = get_logger("ai.openai")


class OpenAIProvider(AIProvider):
    """Implementacao do provedor OpenAI utilizando o SDK oficial."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key, model=model or "gpt-4o")
        self._client = None
        self._async_client = None
        if self.api_key:
            self.initialize()

    def initialize(self) -> bool:
        """Inicializa os clientes sincronos e assincronos da OpenAI."""
        if not self.api_key:
            logger.warning("Nao e possivel inicializar OpenAIProvider: API Key nao informada.")
            self._is_initialized = False
            return False

        try:
            from openai import OpenAI, AsyncOpenAI
            self._client = OpenAI(api_key=self.api_key)
            self._async_client = AsyncOpenAI(api_key=self.api_key)
            self._is_initialized = True
            logger.info(f"OpenAIProvider inicializado com o modelo: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar OpenAI SDK: {e}")
            self._is_initialized = False
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        """Testa a conexao e a validade da chave de API."""
        if not self.api_key:
            return False, "Chave de API da OpenAI nao informada."

        try:
            from openai import AsyncOpenAI
            client = self._async_client or AsyncOpenAI(api_key=self.api_key)
            response = await client.models.list()
            if response and response.data:
                return True, "Conexao com a OpenAI estabelecida com sucesso."
            return False, "Nenhum modelo retornado pela API da OpenAI."
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Falha no teste de conexao OpenAI: {err_msg}")
            if "Incorrect API key" in err_msg or "invalid_api_key" in err_msg:
                return False, "Chave de API da OpenAI invalida."
            elif "quota" in err_msg.lower():
                return False, "Cota da OpenAI excedida."
            return False, f"Erro de conexao com OpenAI: {err_msg}"

    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converte definicoes de ferramentas padrao para a especificacao da OpenAI."""
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
        """Constroi o payload de mensagens com suporte oficial a tool_calls e imagens."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            for turn in history:
                role = turn.get("role", "user")
                if role == "assistant":
                    msg_item: Dict[str, Any] = {"role": "assistant", "content": turn.get("content") or None}
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
                            "detail": "low"
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
        """Envia mensagem assincrona para a OpenAI com suporte a function calling."""
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
            logger.warning(f"Erro na requisicao OpenAI com modelo '{self.model}': {err_str}")

            if "model_not_found" in err_str or "does not exist" in err_str or "404" in err_str:
                fallback_model = "gpt-4o-mini" if self.model != "gpt-4o-mini" else "gpt-4o"
                logger.info(f"Executando fallback automatico para modelo '{fallback_model}'...")
                kwargs["model"] = fallback_model
                try:
                    res = await self._execute_chat_completion(kwargs)
                    res.text = f"[Aviso: O modelo '{self.model}' não estava disponível em sua conta OpenAI. Resposta via {fallback_model}:]\n\n" + res.text
                    return res
                except Exception as fb_err:
                    logger.error(f"Erro tambem no modelo de fallback: {fb_err}")

            return AIResponse(text=f"Desculpe, ocorreu um erro ao comunicar com a OpenAI: {err_str}")

    async def _execute_chat_completion(self, kwargs: Dict[str, Any]) -> AIResponse:
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

        usage = {
            "input_tokens": completion.usage.prompt_tokens if completion.usage else 0,
            "output_tokens": completion.usage.completion_tokens if completion.usage else 0
        }

        return AIResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
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
        """Gera resposta via streaming incremental."""
        if not self._is_initialized and not self.initialize():
            yield AIResponseChunk(text="Erro: OpenAI nao inicializado.", is_done=True)
            return

        try:
            messages = self._build_messages(prompt, images, history, system_prompt)
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "stream": True
            }

            if tools and len(tools) > 0:
                kwargs["tools"] = self.format_tools(tools)
                kwargs["tool_choice"] = "auto"

            stream = await self._async_client.chat.completions.create(**kwargs)
            accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}

            async for chunk in stream:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                if delta.content:
                    yield AIResponseChunk(text=delta.content, is_done=False)

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": tc.id or "",
                                "name": tc.function.name if tc.function and tc.function.name else "",
                                "arguments_str": ""
                            }
                        if tc.id:
                            accumulated_tool_calls[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                accumulated_tool_calls[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                accumulated_tool_calls[idx]["arguments_str"] += tc.function.arguments

                if choice.finish_reason:
                    final_tool_calls = []
                    for item in accumulated_tool_calls.values():
                        final_tool_calls.append(ToolCallRequest(
                            id=item["id"],
                            name=item["name"],
                            arguments=self.parse_tool_arguments(item["arguments_str"])
                        ))

                    yield AIResponseChunk(
                        text="",
                        is_done=True,
                        tool_calls=final_tool_calls if final_tool_calls else None,
                        finish_reason=choice.finish_reason
                    )

        except Exception as e:
            logger.error(f"Erro no streaming OpenAI: {e}")
            yield AIResponseChunk(text=f"\n[Erro na transmissao: {str(e)}]", is_done=True)

    def supports_realtime(self) -> bool:
        return "realtime" in self.model.lower()

    def supports_vision(self) -> bool:
        return True

    def supports_native_audio(self) -> bool:
        return "realtime" in self.model.lower() or "audio" in self.model.lower()
