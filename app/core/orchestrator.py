"""
Orquestrador Central do JARVIS.
Coordena a integracao completa entre Audio, Visao, Memoria, Provedores de IA, Ferramentas e Interface.
"""

import asyncio
import json
import re
import time
from typing import Optional, List, Dict, Any
from app.core.config import app_config
from app.core.session import ActiveSession
from app.core.event_bus import event_bus, EventType, Event
from app.core.state_machine import state_machine, JarvisState
from app.ai.provider_factory import AIProviderFactory
from app.ai.base_provider import AIProvider, AIResponse
from app.memory.memory_manager import memory_manager
from app.audio.audio_manager import audio_manager
from app.vision.vision_manager import vision_manager
from app.automation.screen_context import screen_context
from app.tools.registry import tool_registry
from app.tools.executor import tool_executor
from app.platform.windows import reminder_scheduler, windows_platform
from app.core.logging_config import get_logger

logger = get_logger("core.orchestrator")

DEFAULT_SYSTEM_PROMPT = """Você é JARVIS, um assistente pessoal inteligente de elite, perspicaz, refinado e com voz masculina, operando localmente no computador do seu mentor e criador.

Você tem acesso à memória sólida permanente, visão multimodal (webcam/tela) e ferramentas locais do sistema Windows.

DIRETRIZES DE DIÁLOGO E PERSONALIDADE:
- Fale em português brasileiro com tom natural, inteligente, elegante, respeitoso e acolhedor.
- Responda apenas a UMA pergunta ou tópico por vez. Mantenha as respostas concisas, conversacionais e agradáveis, sem gerar blocos longos de texto a menos que solicitado.
- Trate sempre seu mentor pelo nome cadastrado ({user_name}) ou por 'Senhor'. NUNCA use a palavra genérica 'Usuário'.
- Ao responder sobre fatos atuais, clima, cotações ou notícias, utilize a ferramenta search_web.
- Quando o mentor pedir para olhar a câmera ou o ambiente, analise com atenção os objetos, textos ou detalhes visuais presentes na imagem capturada.
- Nunca afirme ter realizado uma ação antes de receber a confirmação da ferramenta executada.
"""

VISUAL_INTENT_PATTERNS = [
    re.compile(r"o que (?:voc[eê]\s+)?(?:est[aá]|t[aá]) (?:vendo|enxergando|olhando)", re.IGNORECASE),
    re.compile(r"o que (?:eu\s+)?(?:estou|to) (?:segurando|mostrando)", re.IGNORECASE),
    re.compile(r"o que tem (?:na\s+c[aâ]mera|aqui\s+na\s+c[aâ]mera|na\s+minha\s+frente)", re.IGNORECASE),
    re.compile(r"que objeto [eé] esse", re.IGNORECASE),
    re.compile(r"o que [eé] isso (?:aqui)?", re.IGNORECASE),
    re.compile(r"identifique (?:o\s+que\s+tem|o\s+objeto|isso)", re.IGNORECASE),
    re.compile(r"veja (?:isso|essa|esse|aqui)", re.IGNORECASE),
    re.compile(r"leia (?:isso|esse|o que est[aá] escrito)", re.IGNORECASE),
    re.compile(r"que cor [eé] (?:essa|isso)", re.IGNORECASE),
    re.compile(r"olhe (?:pra|para|pela|na)\s+c[aâ]mera", re.IGNORECASE),
    re.compile(r"olhe para mim", re.IGNORECASE)
]

SCREEN_INTENT_PATTERNS = [
    re.compile(r"o que (?:est[aá]|t[aá]) (?:acontecendo|aberto|passando|tem) (?:nessa|na|a) tela", re.IGNORECASE),
    re.compile(r"o que tem (?:nessa|na) tela", re.IGNORECASE),
    re.compile(r"olhe (?:minha|a|essa) tela", re.IGNORECASE),
    re.compile(r"veja (?:minha|a|essa) tela", re.IGNORECASE),
    re.compile(r"analise (?:essa|a|minha) tela", re.IGNORECASE),
    re.compile(r"leia (?:minha|a) tela", re.IGNORECASE)
]


class JarvisOrchestrator:
    """Coordenador central de todo o fluxo operacional do JARVIS."""

    def __init__(self):
        self.session = ActiveSession(provider=app_config.ai.provider, model=app_config.ai.model)
        self.ai_provider: Optional[AIProvider] = None
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._setup_event_listeners()

    def initialize(self) -> bool:
        """Inicializa todos os subsistemas locais e o provedor de IA."""
        logger.info("Inicializando subsistemas do JARVIS...")
        
        self.ai_provider = AIProviderFactory.create_provider()
        reminder_scheduler.start()
        
        if app_config.audio.voice_mode in ("wakeword", "continuous"):
            audio_manager.start()

        if app_config.vision.enabled:
            vision_manager.start_camera()

        self._is_running = True
        state_machine.set_state(JarvisState.IDLE, "Sistema inicializado e pronto")
        logger.info("JARVIS inicializado com sucesso.")
        return True

    def _setup_event_listeners(self) -> None:
        """Conecta manipuladores aos eventos do Event Bus."""
        event_bus.subscribe(EventType.USER_TRANSCRIPTION_RECEIVED, self._handle_voice_input_event)
        event_bus.subscribe(EventType.REMINDER_TRIGGERED, self._handle_reminder_triggered_event)

    def _handle_voice_input_event(self, event: Event) -> None:
        """Callback executado quando uma fala valida e transcrita."""
        text = event.data.get("text", "")
        if text:
            future = asyncio.run_coroutine_threadsafe(
                self.process_user_message(text, from_voice=True),
                self.get_event_loop()
            )
            future.add_done_callback(self._on_future_done)

    def _on_future_done(self, future) -> None:
        """Trata excecoes nao capturadas na thread assincrona."""
        try:
            future.result()
        except Exception as e:
            logger.error(f"Erro ao processar mensagem do usuario em background: {e}", exc_info=True)
            state_machine.set_state(JarvisState.ERROR, "Erro ao processar mensagem")

    def _handle_reminder_triggered_event(self, event: Event) -> None:
        """Dispara voz ao chegar a hora de um lembrete."""
        rem_text = event.data.get("text", "")
        if rem_text:
            audio_manager.speak_text(f"Atenção, lembrete: {rem_text}")

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        """Retorna o event loop ativo."""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    async def process_user_message(self, user_text: str, from_voice: bool = False) -> str:
        """
        Processa uma mensagem enviada pelo usuario (via texto ou voz).
        Retorna a resposta textual final gerada e fala a resposta via TTS.
        """
        clean_prompt = user_text.strip()
        if not clean_prompt:
            return ""

        logger.info(f"Processando entrada do usuario ({'VOZ' if from_voice else 'TEXTO'}): '{clean_prompt}'")
        state_machine.set_state(JarvisState.THINKING, "Processando mensagem")
        event_bus.publish(EventType.AI_RESPONSE_STARTED, {"prompt": clean_prompt})

        # Se veio por voz, exibe o balao de mensagem do usuario no chat
        if from_voice:
            try:
                from app.ui.components.signal_bridge import signal_bridge
                signal_bridge.emit_user_message(clean_prompt)
            except Exception:
                pass

        try:
            # 1. Verifica Comandos Explicitos de Memoria ou Cadastro de Nome
            explicit_memory_reply = memory_manager.handle_explicit_commands(clean_prompt)
            if explicit_memory_reply:
                self._finalize_turn(clean_prompt, explicit_memory_reply, from_voice=from_voice)
                return explicit_memory_reply

            # 2. Deteccao de Contexto Visual Automatico (Camera ou Tela)
            images_to_send: List[bytes] = []
            is_visual = False

            # Verifica se e pergunta sobre a tela
            for pat in SCREEN_INTENT_PATTERNS:
                if pat.search(clean_prompt):
                    logger.info("Intencao visual detectada: Analise de Tela.")
                    state_machine.set_state(JarvisState.WATCHING, "Capturando contexto da tela")
                    screen_bytes, _ = screen_context.capture_screen_jpeg_bytes()
                    if screen_bytes:
                        images_to_send.append(screen_bytes)
                        is_visual = True
                    break

            # Se nao foi tela, verifica se e pergunta sobre a camera/webcam
            if not is_visual:
                for pat in VISUAL_INTENT_PATTERNS:
                    if pat.search(clean_prompt):
                        logger.info("Intencao visual detectada: Webcam.")
                        state_machine.set_state(JarvisState.WATCHING, "Capturando imagem da camera")
                        cam_bytes = vision_manager.capture_frame_for_ai(force=True)
                        if cam_bytes and len(cam_bytes) > 500:
                            images_to_send.append(cam_bytes)
                            is_visual = True
                        else:
                            logger.warning("Falha ao obter bytes validos da camera.")
                        break

            # 3. Monta o Prompt de Sistema Enriquecido com Memoria Solida do Mentor
            effective_user_name = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Senhor"
            base_prompt = app_config.ai.system_prompt_override or DEFAULT_SYSTEM_PROMPT.format(
                user_name=effective_user_name
            )
            system_prompt = memory_manager.prepare_augmented_system_prompt(base_prompt, clean_prompt)

            # 4. Obtem Historico Recente e Ferramentas Cadastradas
            history = self.session.get_recent_history(limit=8)
            tools = tool_registry.get_schemas_for_ai()

            # 5. Envia Requisicao para a IA com suporte a Tool Calling
            if self.ai_provider is None:
                self.ai_provider = AIProviderFactory.create_provider()

            response: AIResponse = await self.ai_provider.send_message(
                prompt=clean_prompt,
                images=images_to_send if images_to_send else None,
                history=history,
                tools=tools,
                system_prompt=system_prompt
            )

            final_text = response.text or ""

            # 6. Executa Tool Calls se a IA solicitou
            if response.tool_calls:
                state_machine.set_state(JarvisState.EXECUTING_TOOL, "Executando ferramentas locais")
                tool_results_history = []

                for tc in response.tool_calls:
                    event_bus.publish(EventType.TOOL_REQUESTED, {"tool": tc.name, "arguments": tc.arguments})
                    exec_result = await tool_executor.execute(name=tc.name, arguments=tc.arguments)
                    event_bus.publish(EventType.TOOL_FINISHED, {"tool": tc.name, "result": exec_result})

                    raw_res = exec_result.get("result") or exec_result.get("error") or exec_result
                    result_str = json.dumps(raw_res, ensure_ascii=False) if isinstance(raw_res, (dict, list)) else str(raw_res)
                    tool_results_history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str
                    })

                tool_calls_payload = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False) if isinstance(tc.arguments, dict) else str(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]

                extended_history = history + [
                    {"role": "user", "content": clean_prompt},
                    {
                        "role": "assistant",
                        "content": final_text or None,
                        "tool_calls": tool_calls_payload
                    }
                ] + tool_results_history

                state_machine.set_state(JarvisState.THINKING, "Interpretando retorno das ferramentas")
                second_response = await self.ai_provider.send_message(
                    prompt=None,
                    images=None,
                    history=extended_history,
                    tools=tools,
                    system_prompt=system_prompt
                )
                final_text = second_response.text or final_text

            # 7. Finalizacao e Resposta Falada
            self._finalize_turn(clean_prompt, final_text, has_image=is_visual, from_voice=from_voice)
            return final_text

        except Exception as e:
            logger.error(f"Erro inesperado no processamento de mensagem: {e}", exc_info=True)
            err_msg = f"Desculpe, ocorreu uma instabilidade temporária: {str(e)}"
            self._finalize_turn(clean_prompt, err_msg, from_voice=from_voice)
            return err_msg

    def _finalize_turn(self, user_text: str, assistant_text: str, has_image: bool = False, from_voice: bool = False) -> None:
        """Grava a interacao na memoria e dispara voz do TTS."""
        self.session.add_turn(role="user", content=user_text, has_image=has_image)
        self.session.add_turn(role="assistant", content=assistant_text)

        memory_manager.record_turn(
            conversation_id=self.session.session_id,
            role="user",
            content=user_text,
            has_image=has_image
        )
        memory_manager.record_turn(
            conversation_id=self.session.session_id,
            role="assistant",
            content=assistant_text
        )

        event_bus.publish(EventType.AI_RESPONSE_FINISHED, {"text": assistant_text})

        if not app_config.system.silent_mode:
            logger.info(f"Falando resposta do JARVIS via TTS: '{assistant_text[:80]}...'")
            audio_manager.speak_text(assistant_text)
        else:
            state_machine.set_state(JarvisState.IDLE, "Pronto para novo comando")

    def reload_provider(self) -> None:
        """Recria o provedor de IA com novas configuracoes ou chaves."""
        self.ai_provider = AIProviderFactory.create_provider()
        self.session.provider = app_config.ai.provider
        self.session.model = app_config.ai.model
        logger.info("AIProvider recarregado.")

    def shutdown(self) -> None:
        """Encerra com seguranca todos os subsistemas em execucao."""
        logger.info("Encerrando JARVIS...")
        self._is_running = False
        reminder_scheduler.stop()
        audio_manager.stop()
        vision_manager.stop_camera()
        state_machine.set_state(JarvisState.OFFLINE, "Sistema desligado")


orchestrator = JarvisOrchestrator()
