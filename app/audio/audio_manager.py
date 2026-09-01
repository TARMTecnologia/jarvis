"""
Gerenciador Central do Subsistema de Audio e Voz do JARVIS.
Garante reproducao ininterrupta da fala do assistente sem cortes por eco e mantem dialogo fluido com janela de continuacao de 8s.
"""

import re
import time
import threading
import numpy as np
from typing import Optional, Callable
from app.audio.microphone import microphone, MicrophoneManager
from app.audio.speaker import speaker, SpeakerManager
from app.audio.vad import vad_detector, VoiceActivityDetector
from app.audio.wakeword import wake_word_detector, WakeWordDetector
from app.audio.stt import local_stt, LocalSTT
from app.audio.tts import local_tts, LocalTTS
from app.audio.speaker_id import speaker_identifier, SpeakerIdentifier
from app.core.event_bus import event_bus, EventType
from app.core.state_machine import state_machine, JarvisState
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.manager")


class AudioManager:
    """Coordenador do pipeline de escuta contínua, supressão de eco e fala sem cortes."""

    def __init__(self):
        self.microphone: MicrophoneManager = microphone
        self.speaker: SpeakerManager = speaker
        self.vad: VoiceActivityDetector = vad_detector
        self.wakeword: WakeWordDetector = wake_word_detector
        self.stt: LocalSTT = local_stt
        self.tts: LocalTTS = local_tts
        self.speaker_id: SpeakerIdentifier = speaker_identifier

        self._is_active = False
        self._is_jarvis_speaking = False
        self._last_spoken_text = ""
        self._last_speech_end_time = 0.0

        self._setup_internal_listeners()

    def _setup_internal_listeners(self) -> None:
        """Configura os callbacks internos de VAD e Microfone."""
        self.microphone.add_callback(self._on_mic_frame)
        self.vad.set_callbacks(
            on_started=self._on_user_speech_start,
            on_finished=self._on_user_speech_finish
        )

    def start(self) -> bool:
        """Inicia a escuta do microfone e VAD."""
        if self._is_active:
            return True

        success = self.microphone.start()
        if success:
            self._is_active = True
            logger.info("AudioManager ativo e ouvindo.")
        return success

    def stop(self) -> None:
        """Interrompe microfone e para qualquer reprodução de áudio."""
        self._is_active = False
        self.microphone.stop()
        self.speaker.stop()
        self.tts.stop()
        self.vad.reset()
        self.wakeword.reset_followup()
        logger.info("AudioManager desativado.")

    def _on_mic_frame(self, frame: np.ndarray, rms: float) -> None:
        """Recebe frames do microfone e alimenta VU Meter e VAD."""
        event_bus.publish(EventType.AUDIO_LEVEL_CHANGED, {"rms": rms})

        # Quando o Jarvis está falando:
        # NUNCA interrompe a própria fala por eco de alto-falante.
        # Permite que ele fale toda a frase do início ao fim sem cortar.
        if self._is_jarvis_speaking:
            return

        self.vad.process_frame(frame, rms)

    def _on_user_speech_start(self) -> None:
        """Disparado no exato instante em que o usuário começa a falar."""
        event_bus.publish(EventType.USER_SPEECH_STARTED)
        state_machine.set_state(JarvisState.LISTENING, "Voz detectada pelo microfone")

    def _on_user_speech_finish(self, audio_data: np.ndarray) -> None:
        """Disparado quando o usuário termina de falar."""
        event_bus.publish(EventType.USER_SPEECH_FINISHED)
        state_machine.set_state(JarvisState.THINKING, "Processando fala")

        threading.Thread(
            target=self._process_transcription_worker,
            args=(audio_data,),
            daemon=True
        ).start()

    def _process_transcription_worker(self, audio_data: np.ndarray) -> None:
        """Executa transcrição local, filtro de eco, modo ditado e validação de ativação."""
        # 1. Transcrição STT
        text = self.stt.transcribe(audio_data)
        if not text or not text.strip():
            state_machine.set_state(JarvisState.IDLE, "Nenhuma fala compreendida")
            return

        # 2. Supressão Inteligente de Eco (Echo Detection)
        now = time.time()
        if (now - self._last_speech_end_time) < 3.0 and self._last_spoken_text:
            text_clean = re.sub(r"[^\w\s]", "", text.lower()).strip()
            last_clean = re.sub(r"[^\w\s]", "", self._last_spoken_text.lower()).strip()
            if text_clean and (text_clean in last_clean or last_clean in text_clean):
                logger.info(f"Eco detectado e descartado: '{text}'")
                state_machine.set_state(JarvisState.IDLE, "Eco descartado")
                return

        # 3. Modo Ditado (WisprFlow offline)
        from app.automation.dictation import dictation_manager
        if dictation_manager.is_active:
            logger.info(f"Inserindo texto ditado na janela ativa: '{text}'")
            dictation_manager.type_text_into_active_window(text)
            state_machine.set_state(JarvisState.IDLE, "Texto ditado colado")
            return

        # 4. Comandos de parada (Barge-in verbal)
        if self.wakeword.is_stop_command(text):
            logger.info(f"Comando de parada recebido via voz: '{text}'")
            self.interrupt_speech()
            state_machine.set_state(JarvisState.IDLE, "Comando de parada")
            return

        # 5. Verifica ativação (Wake Word ou Janela de Continuação de 8s)
        activated, clean_prompt = self.wakeword.process_transcription(text)

        if activated:
            self.wakeword.reset_followup()
            event_bus.publish(
                EventType.USER_TRANSCRIPTION_RECEIVED,
                {"text": clean_prompt or text, "raw_transcription": text}
            )
        else:
            state_machine.set_state(JarvisState.IDLE, "Aguardando wake word")

    def speak_text(self, text: str, on_finished: Optional[Callable[[], None]] = None) -> None:
        """Fala a resposta do Jarvis usando TTS local masculino sem cortes."""
        if not text or not text.strip() or app_config.system.silent_mode:
            if on_finished:
                on_finished()
            return

        def _worker():
            self._is_jarvis_speaking = True
            self._last_spoken_text = text[:150]
            state_machine.set_state(JarvisState.SPEAKING, "Sintetizando voz do assistente")
            event_bus.publish(EventType.SPEAKER_STARTED, {"text": text})

            try:
                self.tts.speak(text)
            finally:
                self._is_jarvis_speaking = False
                self._last_speech_end_time = time.time()
                # Inicia janela de continuação de diálogo de 8 segundos
                self.wakeword.start_followup_window(8.0)
                event_bus.publish(EventType.SPEAKER_FINISHED)
                state_machine.set_state(JarvisState.IDLE, "Ouvindo continuação do diálogo")
                if on_finished:
                    try:
                        on_finished()
                    except Exception as e:
                        logger.error(f"Erro no callback on_finished do TTS: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def interrupt_speech(self) -> None:
        """Interrompe a fala do Jarvis imediatamente se requisitado."""
        self._is_jarvis_speaking = False
        self.tts.stop()
        self.speaker.stop()
        self.wakeword.reset_followup()
        event_bus.publish(EventType.SPEAKER_INTERRUPTED)


audio_manager = AudioManager()
