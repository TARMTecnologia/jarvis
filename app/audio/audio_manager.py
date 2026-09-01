"""
Gerenciador Central do Subsistema de Audio e Voz do JARVIS.
Controla microfone, VAD, STT, Speaker ID exclusivo do mentor, supressao de ruidos e parada verbal imediata ("pare jarvis").
"""

import re
import time
import threading
from collections import deque
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
    """Coordenador do pipeline de voz, identificacao de mentor e interrupcao verbal instantanea."""

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
        self._speaking_mic_buffer = deque(maxlen=25)  # Buffer de 0.8s durante fala para barge-in verbal
        self._checking_barge_in = False

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
        """Recebe frames do microfone, alimenta VU Meter e gerencia barge-in verbal em tempo real."""
        event_bus.publish(EventType.AUDIO_LEVEL_CHANGED, {"rms": rms})

        # Quando o Jarvis estiver falando:
        if self._is_jarvis_speaking:
            self._speaking_mic_buffer.append(frame)
            # Se detectar voz alta humana por cima da fala do robô, checa comando de parada ("pare jarvis")
            if rms > 0.035 and not self._checking_barge_in and len(self._speaking_mic_buffer) >= 15:
                self._checking_barge_in = True
                audio_snippet = np.concatenate(list(self._speaking_mic_buffer))
                threading.Thread(target=self._check_stop_during_speech, args=(audio_snippet,), daemon=True).start()
            return

        self.vad.process_frame(frame, rms)

    def _check_stop_during_speech(self, audio_data: np.ndarray) -> None:
        """Analisa de forma ultra-rápida se o usuário disse 'pare', 'pare jarvis' ou 'silêncio' durante a fala."""
        try:
            quick_text = self.stt.transcribe(audio_data)
            if quick_text and self.wakeword.is_stop_command(quick_text):
                logger.info(f"Comando de parada verbal detectado durante a fala: '{quick_text}'. Interrompendo imediatamente!")
                self.interrupt_speech()
        except Exception as e:
            logger.debug(f"Erro ao checar comando de parada: {e}")
        finally:
            self._checking_barge_in = False

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
        """Executa verificacao do mentor, transcrição local, filtro de eco, modo ditado e validação."""
        # 1. Filtro Exclusivo da Voz do Mentor (Speaker ID)
        if getattr(app_config.audio, "mentor_voice_filter_enabled", False):
            is_mentor, similarity = self.speaker_id.is_mentor_voice(audio_data)
            if not is_mentor:
                user_name = app_config.system.user_name if app_config.system.user_name != "Usuário" else "meu mentor"
                logger.info(f"Voz de terceiro rejeitada (Similaridade: {similarity:.2f}). Informando que apenas {user_name} pode comandar.")
                rejection_msg = f"Desculpe, mas não posso ajudar porque quem está falando não é {user_name}."
                self.speak_text(rejection_msg)
                return

        # 2. Transcrição STT
        text = self.stt.transcribe(audio_data)
        if not text or not text.strip():
            state_machine.set_state(JarvisState.IDLE, "Nenhuma fala compreendida")
            return

        # 3. Supressão Inteligente de Eco
        now = time.time()
        if (now - self._last_speech_end_time) < 3.0 and self._last_spoken_text:
            text_clean = re.sub(r"[^\w\s]", "", text.lower()).strip()
            last_clean = re.sub(r"[^\w\s]", "", self._last_spoken_text.lower()).strip()
            if text_clean and (text_clean in last_clean or last_clean in text_clean):
                logger.info(f"Eco detectado e descartado: '{text}'")
                state_machine.set_state(JarvisState.IDLE, "Eco descartado")
                return

        # 4. Modo Ditado (WisprFlow offline)
        from app.automation.dictation import dictation_manager
        if dictation_manager.is_active:
            logger.info(f"Inserindo texto ditado na janela ativa: '{text}'")
            dictation_manager.type_text_into_active_window(text)
            state_machine.set_state(JarvisState.IDLE, "Texto ditado colado")
            return

        # 5. Comandos de parada imediatos
        if self.wakeword.is_stop_command(text):
            logger.info(f"Comando de parada recebido via voz: '{text}'")
            self.interrupt_speech()
            state_machine.set_state(JarvisState.IDLE, "Comando de parada")
            return

        # 6. Verifica ativação (Wake Word ou Janela de Continuação de 8s)
        activated, clean_prompt = self.wakeword.process_transcription(text)

        if activated:
            self.wakeword.reset_followup()
            event_bus.publish(
                EventType.USER_TRANSCRIPTION_RECEIVED,
                {"text": clean_prompt or text, "raw_transcription": text, "audio_data": audio_data}
            )
        else:
            state_machine.set_state(JarvisState.IDLE, "Aguardando wake word")

    def speak_text(self, text: str, on_finished: Optional[Callable[[], None]] = None) -> None:
        """Fala a resposta do Jarvis usando voz masculina neural acelerada e fluida."""
        if not text or not text.strip() or app_config.system.silent_mode:
            if on_finished:
                on_finished()
            return

        def _worker():
            self._is_jarvis_speaking = True
            self._speaking_mic_buffer.clear()
            self._last_spoken_text = text[:150]
            state_machine.set_state(JarvisState.SPEAKING, "Sintetizando voz do assistente")
            event_bus.publish(EventType.SPEAKER_STARTED, {"text": text})

            try:
                self.tts.speak(text)
            finally:
                self._is_jarvis_speaking = False
                self._speaking_mic_buffer.clear()
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
        """Interrompe a fala do Jarvis imediatamente (<20ms)."""
        self._is_jarvis_speaking = False
        self._speaking_mic_buffer.clear()
        self.tts.stop()
        self.speaker.stop()
        self.wakeword.reset_followup()
        state_machine.set_state(JarvisState.IDLE, "Fala interrompida pelo mentor")
        event_bus.publish(EventType.SPEAKER_INTERRUPTED)


audio_manager = AudioManager()
