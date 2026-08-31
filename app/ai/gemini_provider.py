"""
Provedor de IA Google Gemini para o JARVIS.
Suporta modelos Gemini 2.0 Flash, Gemini 1.5 Pro/Flash, visão multimodal e function calling.
"""

import io
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from PIL import Image
from app.ai.base_provider import AIProvider, AIResponse, AIResponseChunk, ToolCallRequest
from app.core.logging_config import get_logger

logger = get_logger("ai.gemini")


class GeminiProvider(AIProvider):
    """Implementação do provedor Google Gemini utilizando o SDK oficial."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key, model=model or "gemini-2.0-flash")
        self._client = None
        if self.api_key:
            self.initialize()

    def initialize(self) -> bool:
        """Inicializa o SDK do Google Gemini."""
        if not self.api_key:
            logger.warning("Não é possível inicializar GeminiProvider: API Key não informada.")
            self._is_initialized = False
            return False

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._is_initialized = True
            logger.info(f"GeminiProvider inicializado com o modelo: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar Gemini SDK: {e}")
            self._is_initialized = False
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        """Testa a conexão e validade da chave do Google Gemini."""
        if not self.api_key:
            return False, "Chave de API do Gemini não informada."

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            models = list(genai.list_models())
            if models:
                return True, "Conexão com o Google Gemini estabelecida com sucesso."
            return False, "Nenhum modelo retornado pelo Google Gemini."
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Falha no teste de conexão Gemini: {err_msg}")
            if "API_KEY_INVALID" in err_msg or "invalid" in err_msg.lower():
                return False, "Chave de API do Google Gemini inválida."
            elif "quota" in err_msg.lower() or "resource_exhausted" in err_msg.lower():
                return False, "Cota do Google Gemini excedida."
            return False, f"Erro de conexão com Gemini: {err_msg}"

    def format_tools(self, tools: List[Dict[str, Any]]) -> Any:
        """Converte as ferramentas para a especificação do Gemini."""
        return tools

    def _convert_images(self, images: Optional[List[bytes]]) -> List[Any]:
        """Converte bytes em objetos PIL Image para o Gemini."""
        pil_images = []
        if images:
            for img_bytes in images:
                try:
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    pil_images.append(pil_img)
                except Exception as e:
                    logger.error(f"Erro ao converter imagem para PIL: {e}")
        return pil_images

    async def send_message(
        self,
        prompt: str,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AIResponse:
        """Envia requisição para o Google Gemini."""
        if not self._is_initialized and not self.initialize():
            return AIResponse(text="Erro: Provedor Gemini não está inicializado com uma chave válida.")

        try:
            import google.generativeai as genai

            generation_config = genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )

            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt if system_prompt else None,
                generation_config=generation_config
            )

            if history:
                chat = model.start_chat(history=[])
                for turn in history:
                    role = "user" if turn.get("role") == "user" else "model"
                    content_str = turn.get("content", "")
                    if content_str:
                        chat.history.append(genai.types.content_types.to_content({
                            "role": role,
                            "parts": [content_str]
                        }))

                pil_imgs = self._convert_images(images)
                current_parts = [prompt] + pil_imgs
                response = await chat.send_message_async(current_parts)
            else:
                pil_imgs = self._convert_images(images)
                contents = [prompt] + pil_imgs
                response = await model.generate_content_async(contents)

            text_output = ""
            try:
                text_output = response.text
            except Exception:
                if response.parts:
                    text_output = "".join(part.text for part in response.parts if hasattr(part, "text"))

            tool_calls = []
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            args_dict = dict(fc.args) if hasattr(fc, "args") else {}
                            tool_calls.append(ToolCallRequest(
                                id=fc.name,
                                name=fc.name,
                                arguments=args_dict
                            ))

            return AIResponse(
                text=text_output,
                tool_calls=tool_calls,
                finish_reason="stop",
                raw_response=response
            )

        except Exception as e:
            logger.error(f"Erro na requisição Gemini: {e}")
            return AIResponse(text=f"Desculpe, ocorreu um erro ao comunicar com o Google Gemini: {str(e)}")

    async def stream_response(
        self,
        prompt: str,
        images: Optional[List[bytes]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[AIResponseChunk, None]:
        """Gera resposta streaming do Google Gemini."""
        if not self._is_initialized and not self.initialize():
            yield AIResponseChunk(text="Erro: Gemini não inicializado.", is_done=True)
            return

        try:
            import google.generativeai as genai

            model = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=system_prompt if system_prompt else None
            )

            pil_imgs = self._convert_images(images)
            contents = [prompt] + pil_imgs

            response = await model.generate_content_async(contents, stream=True)

            async for chunk in response:
                try:
                    if chunk.text:
                        yield AIResponseChunk(text=chunk.text, is_done=False)
                except Exception:
                    pass

            yield AIResponseChunk(text="", is_done=True, finish_reason="stop")

        except Exception as e:
            logger.error(f"Erro no streaming Gemini: {e}")
            yield AIResponseChunk(text=f"\n[Erro no streaming Gemini: {str(e)}]", is_done=True)

    def supports_realtime(self) -> bool:
        return "2.0" in self.model

    def supports_vision(self) -> bool:
        return True

    def supports_native_audio(self) -> bool:
        return False
