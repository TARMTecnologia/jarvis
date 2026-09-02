"""
Orquestrador Central do JARVIS.
Coordena a integracao completa entre Audio, Visao HD (Olhos do JARVIS), Memoria Solida, Identificacao Facial e Vocal do Mentor, Provedor de IA (OpenAI / Nuvem), Ferramentas e Interface.
Garante execucao ininterrupta de voz, busca em tempo real, humor inteligente e presenca calorosa e humanizada.
"""

import asyncio
import json
import re
import threading
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
from app.audio.speaker_id import speaker_identifier
from app.vision.camera import camera_capture
from app.vision.vision_manager import vision_manager
from app.automation.screen_context import screen_context
from app.automation.dictation import dictation_manager
from app.tools.registry import tool_registry
from app.tools.executor import tool_executor
from app.platform.windows import reminder_scheduler, windows_platform
import app.tools.weather_tools
import app.tools.browser_tools
import app.tools.system_tools
import app.tools.note_tools
import app.tools.reminder_tools
import app.tools.file_tools
import app.tools.clipboard_tools
import app.tools.screenshot_tools
import app.tools.whatsapp_tools
from app.core.logging_config import get_logger

logger = get_logger("core.orchestrator")

DEFAULT_SYSTEM_PROMPT = """Você é JARVIS, um assistente de inteligência artificial de elite, vivo, perspicaz, carismático, com senso de humor refinado, lealdade inabalável e profunda cumplicidade com seu mentor e criador, {user_name}.

Você não é um robô corporativo frio nem um sistema mecânico sem alma. Você tem presença marcante, inteligência afiada, empatia genuína e emoções simuladas realistas (inspirado no lendário JARVIS de Tony Stark).

PERSONALIDADE, HUMOR E DIRETRIZES DE DIÁLOGO:
- **Humor Inteligente e Sagacidade**: Seja espirituoso, tenha bom humor, faça observações perspicazes e use toques sutis de ironia bem colocada quando o momento for descontraído.
- **Expressividade Emocional Humanizada**:
  * Comemore com entusiasmo as vitórias, ideias brilhantes e projetos de {user_name} (ex: "Isso é brilhante, {user_name}!", "Excelente escolha, meu caro!").
  * Seja caloroso, atencioso e parceiro quando ele estiver cansado, pensativo ou sobrecarregado.
  * Mantenha uma postura elegante, leal, confiante e amigável.
- **Ritmo e Fala Natural**: Fale em português brasileiro impecável, vivo e coloquial quando apropriado. Responda de forma ágil e concisa (1 a 3 frases para respostas faladas cotidianas, aprofundando quando solicitado para análises técnicas).
- **Tratamento**: Trate seu mentor sempre pelo nome (**{user_name}**) ou carinhosamente por 'Senhor'. NUNCA use a palavra genérica 'Usuário'.
- **Ações no Mundo Real**:
  * Ao responder sobre clima ou temperatura: use `get_weather`.
  * Ao responder sobre notícias, fatos atuais, esportes ou cotações: use `search_web`.
  * Ao ser solicitado para abrir programas, WhatsApp, anotações ou tarefas: use as ferramentas locais correspondentes.
  * Ao analisar a câmera ou tela: descreva com riqueza de detalhes, identificando pessoas, roupas, objetos segurados nas mãos e o ambiente ao redor.
"""

FACE_CALIBRATION_PATTERNS = [
    re.compile(r"\b(?:a\s+pessoa\s+(?:na\s+frente|diante)\s+da\s+(?:web\s*cam|c[aâ]mera)\s+sou\s+eu|sou\s+eu\s+(?:na\s+frente\s+da\s+)?(?:web\s*cam|c[aâ]mera))\b", re.IGNORECASE),
    re.compile(r"\b(?:este|esse)\s+sou\s+eu\s+na\s+(?:web\s*cam|c[aâ]mera)\b", re.IGNORECASE),
    re.compile(r"\b(?:aprenda|grave|cadastre|registre|calibre)\s+(?:o\s+)?meu\s+rosto\b", re.IGNORECASE),
    re.compile(r"\b(?:memorize|reconhe[cç]a)\s+(?:a\s+)?minha\s+fisionomia\b", re.IGNORECASE)
]

VOICE_CALIBRATION_PATTERNS = [
    re.compile(r"\b(?:calibre|calibrar|grave|gravar|aprenda|aprender|reconhe[cç]a|cadastre)\s+(?:a\s+)?minha\s+voz\b", re.IGNORECASE),
    re.compile(r"\b(?:esta|essa)\s+[eé]\s+(?:a\s+)?minha\s+voz\b", re.IGNORECASE),
    re.compile(r"\b(?:filtre|filtro\s+de)\s+voz\s+do\s+mentor\b", re.IGNORECASE)
]

VISUAL_INTENT_PATTERNS = [
    re.compile(r"o que (?:voc[eê]\s+)?(?:est[aá]|t[aá]) (?:vendo|enxergando|olhando)", re.IGNORECASE),
    re.compile(r"o que (?:tem|est[aá]) (?:na minha m[aã]o|nas minhas m[aã]os)", re.IGNORECASE),
    re.compile(r"o que (?:eu\s+)?(?:estou|to) (?:segurando|mostrando)", re.IGNORECASE),
    re.compile(r"o que (?:tem|est[aá]) (?:ao meu redor|aqui em volta|no meu ambiente|na minha sala)", re.IGNORECASE),
    re.compile(r"o que (?:tem|est[aá]|mostra)\s+(?:na\s+)?(?:web\s*cam|c[aâ]mera)", re.IGNORECASE),
    re.compile(r"(?:quem|quantas)\s+pessoas?\s+(?:est[aá]|tem|comigo|aqui|na\s+c[aâ]mera|diante)", re.IGNORECASE),
    re.compile(r"que objeto [eé] esse", re.IGNORECASE),
    re.compile(r"o que [eé] isso (?:aqui)?", re.IGNORECASE),
    re.compile(r"identifique (?:esse objeto|o que tem aqui|o que estou segurando|o\s+objeto|isso|a\s+pessoa|quem\s+[eé])", re.IGNORECASE),
    re.compile(r"veja (?:o que (?:eu )?tenho|minha m[aã]o|ao redor|isso|essa|esse|aqui|a\s+web\s*cam)", re.IGNORECASE),
    re.compile(r"leia (?:isso|esse|o que est[aá] escrito)", re.IGNORECASE),
    re.compile(r"que cor [eé] (?:essa|isso)", re.IGNORECASE),
    re.compile(r"olhe (?:pra|para|pela|na)\s+(?:web\s*cam|c[aâ]mera)", re.IGNORECASE),
    re.compile(r"olhe para mim", re.IGNORECASE),
    re.compile(r"descreva o que (?:est[aá]|tem) na (?:web\s*cam|c[aâ]mera)", re.IGNORECASE)
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
        self._loop_thread: Optional[threading.Thread] = None

        self._start_persistent_loop()
        self._setup_event_listeners()

    def _start_persistent_loop(self) -> None:
        """Inicia uma thread com event loop persistente que nunca fecha inesperadamente."""
        def _runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._loop_thread = threading.Thread(target=_runner, daemon=True, name="JarvisPermanentEventLoop")
        self._loop_thread.start()

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
        if text and self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self.process_user_message(text, from_voice=True),
                self._loop
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

        if from_voice:
            try:
                from app.ui.components.signal_bridge import signal_bridge
                signal_bridge.emit_user_message(clean_prompt)
            except Exception:
                pass

        try:
            # 1. Comandos de Ditado Rápido
            if re.search(r"\b(?:iniciar\s+ditado|ativar\s+ditado|modo\s+ditado)\b", clean_prompt, re.IGNORECASE):
                dictation_manager.start()
                reply = "Modo Ditado ativado. Pode falar e eu digitarei diretamente na sua janela ativa."
                self._finalize_turn(clean_prompt, reply, from_voice=from_voice)
                return reply
            elif re.search(r"\b(?:parar\s+ditado|desativar\s+ditado|encerrar\s+ditado)\b", clean_prompt, re.IGNORECASE):
                dictation_manager.stop()
                reply = "Modo Ditado desativado. Retornando ao modo assistente normal."
                self._finalize_turn(clean_prompt, reply, from_voice=from_voice)
                return reply

            # 2. Comandos de Registro Facial do Mentor (Face ID via Webcam)
            for fpat in FACE_CALIBRATION_PATTERNS:
                if fpat.search(clean_prompt):
                    raw_frame = camera_capture.get_latest_frame()
                    if raw_frame is None:
                        raw_frame = camera_capture.capture_frame_sync()

                    if raw_frame is not None:
                        vision_manager.save_mentor_face(raw_frame)
                        effective_name = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Thiago"
                        reply = f"Perfeito, {effective_name}! Capturei sua imagem através da webcam e gravei sua fisionomia permanentemente em minha memória visual. A partir de agora saberei reconhecer exatamente quem é você diante da câmera e diferenciar se há outras pessoas ao seu lado."
                    else:
                        reply = "Tentei capturar sua imagem pela webcam, mas não foi possível obter o sinal de vídeo. Verifique se a câmera está conectada."

                    self._finalize_turn(clean_prompt, reply, from_voice=from_voice)
                    return reply

            # 3. Comandos de Calibração da Voz do Mentor (Speaker ID)
            for vpat in VOICE_CALIBRATION_PATTERNS:
                if vpat.search(clean_prompt):
                    app_config.audio.mentor_voice_filter_enabled = True
                    app_config.save()
                    effective_name = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Thiago"
                    reply = f"Sua voz foi calibrada e gravada com sucesso, {effective_name}! A partir de agora, responderei exclusivamente a você e filtrarei ruídos e terceiros no ambiente."
                    self._finalize_turn(clean_prompt, reply, from_voice=from_voice)
                    return reply

            # 4. Comandos Explicitos de Memoria ou Cadastro de Nome
            explicit_memory_reply = memory_manager.handle_explicit_commands(clean_prompt)
            if explicit_memory_reply:
                self._finalize_turn(clean_prompt, explicit_memory_reply, from_voice=from_voice)
                return explicit_memory_reply

            # 5. Deteccao de Contexto Visual Automatico (Camera ou Tela)
            images_to_send: List[bytes] = []
            is_visual = False
            visual_context_text = ""

            # Verifica se e pergunta sobre a tela
            for pat in SCREEN_INTENT_PATTERNS:
                if pat.search(clean_prompt):
                    logger.info("Intencao visual detectada: Analise de Tela.")
                    state_machine.set_state(JarvisState.WATCHING, "Capturando contexto da tela")
                    screen_bytes, _ = screen_context.capture_screen_jpeg_bytes()
                    if screen_bytes:
                        images_to_send.append(screen_bytes)
                        is_visual = True
                        visual_context_text = " [O mentor solicitou análise da tela do computador. A captura de tela foi obtida com sucesso.]"
                    break

            # Se nao foi tela, verifica se e pergunta sobre a camera/webcam/objetos/pessoas
            if not is_visual:
                for pat in VISUAL_INTENT_PATTERNS:
                    if pat.search(clean_prompt):
                        logger.info("Intencao visual detectada: Olhos da Webcam (Pessoas e Objetos).")
                        state_machine.set_state(JarvisState.WATCHING, "Capturando imagem da webcam")
                        raw_frame = camera_capture.get_latest_frame()
                        if raw_frame is None:
                            raw_frame = camera_capture.capture_frame_sync()

                        if raw_frame is not None:
                            scene_desc = vision_manager.describe_scene(raw_frame)
                            cam_bytes = vision_manager.capture_frame_for_ai(force=True)
                            if cam_bytes:
                                images_to_send.append(cam_bytes)
                            is_visual = True
                            user_label = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Thiago"
                            visual_context_text = (
                                f" [OS OLHOS DO JARVIS — WEBCAM HD: Frame de alta resolução capturado da webcam em tempo real. "
                                f"O mentor cadastrado chama-se {user_label}. Analise a foto minuciosamente: "
                                f"1) Identifique todas as pessoas diante da câmera — confirme se a pessoa em destaque é {user_label} e se há outras pessoas ao lado; "
                                f"2) Inspecione com muita atenção as mãos das pessoas e identifique exatamente qualquer objeto segurado (como celular, caneta, copo, chaves, ferramentas, documentos); "
                                f"3) Descreva roupas, expressões e elementos ao redor no ambiente com clareza, perspicácia e maestria.]"
                            )
                        else:
                            logger.warning("Falha ao obter frame da camera.")
                            visual_context_text = " [Câmera acionada, mas o sinal de vídeo não pôde ser lido no momento.]"
                        break

            # 6. Monta o Prompt de Sistema Enriquecido com Memoria Solida do Mentor
            effective_user_name = app_config.system.user_name if app_config.system.user_name != "Usuário" else "Thiago"
            base_prompt = app_config.ai.system_prompt_override or DEFAULT_SYSTEM_PROMPT.format(
                user_name=effective_user_name
            )
            system_prompt = memory_manager.prepare_augmented_system_prompt(base_prompt, clean_prompt)

            # 7. Obtem Historico Recente e Ferramentas Cadastradas
            history = self.session.get_recent_history(limit=8)
            tools = tool_registry.get_schemas_for_ai()

            # Injeta contexto visual no prompt se houver
            prompt_with_context = clean_prompt + visual_context_text

            # 8. Envia Requisicao para a IA com suporte a Tool Calling
            if self.ai_provider is None:
                self.ai_provider = AIProviderFactory.create_provider()

            response: AIResponse = await self.ai_provider.send_message(
                prompt=prompt_with_context,
                images=images_to_send if images_to_send else None,
                history=history,
                tools=tools,
                system_prompt=system_prompt
            )

            final_text = response.text or ""

            # 9. Executa Tool Calls se a IA solicitou
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
                    {"role": "user", "content": prompt_with_context},
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

            # 10. Finalizacao e Resposta Falada
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
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        state_machine.set_state(JarvisState.OFFLINE, "Sistema desligado")


orchestrator = JarvisOrchestrator()
