"""
Gerenciador Central do Subsistema de Audio e Voz do JARVIS.
Integra Microfone, VAD, STT, Wake Word, TTS e Barge-in com o barramento de eventos.
"""

import threading
import numpy as np
from typing import Optional, Callable
from app.audio.microphone import microphone, MicrophoneManager
from app.audio.speaker import speaker, SpeakerManager
from app.audio.vad import vad_detector, VoiceActivityDetector
from app.audio.wakeword import wake_word_detector, WakeWordDetector
from app.audio.stt import local_stt, LocalSTT
from app.audio.tts import local_tts, LocalTTS
from app.core.event_bus import event_bus, EventType
from app.core.state_machine import state_machine, JarvisState
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.manager")


class AudioManager:
    """Coordenador completo do pipeline de voz local."""

    def __init__(self):
        self.microphone: MicrophoneManager = microphone
        self.speaker: SpeakerManager = speaker
        self.vad: VoiceActivityDetector = vad_detector
        self.wakeword: WakeWordDetector = wake_word_detector
        self.stt: LocalSTT = local_stt
        self.tts: LocalTTS = local_tts

        self._is_active = False
        self._is_jarvis_speaking = False
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
        logger.info("AudioManager desativado.")

    def _on_mic_frame(self, frame: np.ndarray, rms: float) -> None:
        """Recebe frames do microfone e alimenta VU Meter e VAD."""
        # Publica nível de áudio para animação visual na UI
        event_bus.publish(EventType.AUDIO_LEVEL_CHANGED, {"rms": rms})

        # Se o Jarvis estiver falando e o usuário emitir um som alto: aciona Barge-In
        if self._is_jarvis_speaking:
            if app_config.audio.barge_in_enabled and rms > (app_config.audio.vad_sensitivity * 0.08):
                logger.info("Voz detectada durante a fala do Jarvis. Acionando Barge-In!")
                self.interrupt_speech()
            return  # Suprime alimentação do VAD para não transcrever a própria voz do assistente

        self.vad.process_frame(frame, rms)

    def _on_user_speech_start(self) -> None:
        """Disparado no exato instante em que o usuário começa a falar."""
        event_bus.publish(EventType.USER_SPEECH_STARTED)
        state_machine.set_state(JarvisState.LISTENING, "Voz detectada pelo microfone")

    def _on_user_speech_finish(self, audio_data: np.ndarray) -> None:
        """Disparado quando o usuário termina de falar."""
        event_bus.publish(EventType.USER_SPEECH_FINISHED)
        state_machine.set_state(JarvisState.THINKING, "Processando transcrição local de fala")

        # Transcreve o áudio em background para não travar a thread de áudio
        threading.Thread(
            target=self._process_transcription_worker,
            args=(audio_data,),
            daemon=True
        ).start()

    def _process_transcription_worker(self, audio_data: np.ndarray) -> None:
        """Executa a transcrição local e verifica Wake Word / Comandos de interrupção."""
        text = self.stt.transcribe(audio_data)
        if not text:
            state_machine.set_state(JarvisState.IDLE, "Nenhuma fala compreendida")
            return

        # Verifica se é um comando de parada
        if self.wakeword.is_stop_command(text):
            logger.info(f"Comando de parada recebido via voz: '{text}'")
            self.interrupt_speech()
            state_machine.set_state(JarvisState.IDLE, "Comando de parada")
            return

        # Verifica ativação de acordo com o modo
        activated, clean_prompt = self.wakeword.process_transcription(text)

        if activated:
            event_bus.publish(
                EventType.USER_TRANSCRIPTION_RECEIVED,
                {"text": clean_prompt or text, "raw_transcription": text}
            )
        else:
            state_machine.set_state(JarvisState.IDLE, "Wake word nao detectada")

    def speak_text(self, text: str, on_finished: Optional[Callable[[], None]] = None) -> None:
        """Fala a resposta do Jarvis usando TTS local de forma assíncrona."""
        if not text or not text.strip() or app_config.system.silent_mode:
            if on_finished:
                on_finished()
            return

        def _worker():
            self._is_jarvis_speaking = True
            state_machine.set_state(JarvisState.SPEAKING, "Sintetizando voz do assistente")
            event_bus.publish(EventType.SPEAKER_STARTED, {"text": text})

            try:
                self.tts.speak(text)
            finally:
                self._is_jarvis_speaking = False
                event_bus.publish(EventType.SPEAKER_FINISHED)
                state_machine.set_state(JarvisState.IDLE, "Fala do assistente concluida")
                if on_finished:
                    try:
                        on_finished()
                    except Exception as e:
                        logger.error(f"Erro no callback on_finished do TTS: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def interrupt_speech(self) -> None:
        """Interrompe a fala do Jarvis imediatamente (Barge-in)."""
        self._is_jarvis_speaking = False
        self.tts.stop()
        self.speaker.stop()
        event_bus.publish(EventType.SPEAKER_INTERRUPTED)


audio_manager = AudioManager()
