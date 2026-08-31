"""
Provedor de IA Anthropic Claude para o JARVIS.
Suporta modelos Claude 3.5 Sonnet, Claude 3.5 Haiku, visao multimodal e function calling (tools).
"""

import base64
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from app.ai.base_provider import AIProvider, AIResponse, AIResponseChunk, ToolCallRequest
from app.core.logging_config import get_logger

logger = get_logger("ai.anthropic")


class AnthropicProvider(AIProvider):
    """Implementacao do provedor Anthropic Claude utilizando o SDK oficial."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
        self._client = None
        self._async_client = None
        if self.api_key:
            self.initialize()

    def initialize(self) -> bool:
        """Inicializa os clientes do SDK da Anthropic."""
        if not self.api_key:
            logger.warning("Nao e possivel inicializar AnthropicProvider: API Key nao informada.")
            self._is_initialized = False
            return False

        try:
            from anthropic import Anthropic, AsyncAnthropic
            self._client = Anthropic(api_key=self.api_key)
            self._async_client = AsyncAnthropic(api_key=self.api_key)
            self._is_initialized = True
            logger.info(f"AnthropicProvider inicializado com o modelo: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar Anthropic SDK: {e}")
            self._is_initialized = False
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        """Testa a conexao e a validade da chave de API da Anthropic."""
        if not self.api_key:
            return False, "Chave de API da Anthropic nao informada."

        try:
            from anthropic import AsyncAnthropic
            client = self._async_client or AsyncAnthropic(api_key=self.api_key)
            response = await client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}]
            )
            if response and response.content:
                return True, "Conexao com a Anthropic Claude estabelecida com sucesso."
            return False, "Sem resposta da Anthropic."
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Falha no teste de conexao Anthropic: {err_msg}")
            if "authentication_error" in err_msg.lower() or "invalid x-api-key" in err_msg.lower():
                return False, "Chave de API da Anthropic invalida."
            elif "credit" in err_msg.lower() or "balance" in err_msg.lower():
                return False, "Creditos insuficientes na conta Anthropic."
            return False, f"Erro de conexao com Anthropic: {err_msg}"

    def format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converte definicoes padrao de ferramentas para o formato do Claude."""
        claude_tools = []
        for t in tools:
            claude_tools.append({
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "input_schema": t.get("parameters", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            })
        return claude_tools

    def _build_messages(
        self,
        prompt: str,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Constroi o payload de mensagens com suporte a imagens em base64."""
        messages = []

        if history:
            for turn in history:
                role = turn.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": turn.get("content", "")})

        if images and len(images) > 0:
            content_list: List[Dict[str, Any]] = []
            for img_bytes in images:
                b64_img = base64.b64encode(img_bytes).decode("utf-8")
                content_list.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64_img
                    }
                })
            content_list.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": content_list})
        else:
            messages.append({"role": "user", "content": prompt})

        return messages

    async def send_message(
        self,
        prompt: str,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AIResponse:
        """Envia requisicao para a Anthropic Claude."""
        if not self._is_initialized and not self.initialize():
            return AIResponse(text="Erro: Provedor Claude nao esta inicializado com uma chave valida.")

        try:
            messages = self._build_messages(prompt, images, history)
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": 2048,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if tools and len(tools) > 0:
                kwargs["tools"] = self.format_tools(tools)

            response = await self._async_client.messages.create(**kwargs)

            text_parts = []
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(ToolCallRequest(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {}
                    ))

            usage = {
                "input_tokens": response.usage.input_tokens if response.usage else 0,
                "output_tokens": response.usage.output_tokens if response.usage else 0
            }

            return AIResponse(
                text="".join(text_parts),
                tool_calls=tool_calls,
                finish_reason=response.stop_reason or "stop",
                usage=usage,
                raw_response=response
            )

        except Exception as e:
            logger.error(f"Erro na requisicao Claude: {e}")
            return AIResponse(text=f"Desculpe, ocorreu um erro ao comunicar com a Anthropic Claude: {str(e)}")

    async def stream_response(
        self,
        prompt: str,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[AIResponseChunk, None]:
        """Gera resposta streaming do Anthropic Claude."""
        if not self._is_initialized and not self.initialize():
            yield AIResponseChunk(text="Erro: Claude nao inicializado.", is_done=True)
            return

        try:
            messages = self._build_messages(prompt, images, history)
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": 2048,
                "messages": messages,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if tools and len(tools) > 0:
                kwargs["tools"] = self.format_tools(tools)

            async with self._async_client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield AIResponseChunk(text=text, is_done=False)

                final_message = await stream.get_final_message()
                tool_calls = []
                for block in final_message.content:
                    if block.type == "tool_use":
                        tool_calls.append(ToolCallRequest(
                            id=block.id,
                            name=block.name,
                            arguments=block.input if isinstance(block.input, dict) else {}
                        ))

                yield AIResponseChunk(
                    text="",
                    is_done=True,
                    tool_calls=tool_calls if tool_calls else None,
                    finish_reason=final_message.stop_reason or "stop"
                )

        except Exception as e:
            logger.error(f"Erro no streaming Claude: {e}")
            yield AIResponseChunk(text=f"\n[Erro no streaming Claude: {str(e)}]", is_done=True)

    def supports_realtime(self) -> bool:
        return False

    def supports_vision(self) -> bool:
        return True

    def supports_native_audio(self) -> bool:
        return False
