"""
Sintese de Voz Local (Text-To-Speech) para o JARVIS.
Utiliza a engine nativa SAPI5 do Windows via pyttsx3 com suporte a interrupcao imediata (Barge-in).
"""

import threading
import queue
from typing import List, Dict, Any, Optional, Callable
import pyttsx3
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.tts")


class LocalTTS:
    """Motor de síntese de voz local nativo do Windows."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._engine: Optional[pyttsx3.Engine] = None
        self._init_engine()

    def _init_engine(self) -> None:
        """Inicializa a engine pyttsx3."""
        try:
            self._engine = pyttsx3.init("sapi5")
            self._engine.setProperty("rate", app_config.audio.tts_rate)
            self._engine.setProperty("volume", app_config.audio.tts_volume)
            
            # Se houver voz configurada ou preferência por voz em português
            voices = self._engine.getProperty("voices")
            pt_voice = None
            for v in voices:
                if "portuguese" in v.name.lower() or "brazil" in v.name.lower() or "maria" in v.name.lower() or "daniel" in v.name.lower():
                    pt_voice = v.id
                    break
            
            selected_voice = app_config.audio.tts_voice_id or pt_voice
            if selected_voice:
                self._engine.setProperty("voice", selected_voice)

            logger.info("Motor local SAPI5 TTS inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar pyttsx3 SAPI5: {e}")
            self._engine = None

    def list_voices(self) -> List[Dict[str, Any]]:
        """Lista todas as vozes instaladas no Windows."""
        voice_list = []
        if self._engine is None:
            self._init_engine()

        if self._engine is not None:
            try:
                voices = self._engine.getProperty("voices")
                for v in voices:
                    voice_list.append({
                        "id": v.id,
                        "name": v.name,
                        "languages": getattr(v, "languages", []),
                        "gender": getattr(v, "gender", "unknown")
                    })
            except Exception as e:
                logger.error(f"Erro ao listar vozes SAPI5: {e}")
        return voice_list

    def speak(self, text: str, on_start: Optional[Callable[[], None]] = None, on_end: Optional[Callable[[], None]] = None) -> None:
        """
        Sintetiza e fala o texto síncronamente na thread atual.
        Permite interrupção imediata via stop().
        """
        clean_text = text.strip()
        if not clean_text:
            return

        with self._lock:
            self._is_speaking = True

        if on_start:
            try:
                on_start()
            except Exception:
                pass

        try:
            # Recria a engine por chamada para evitar problemas de loop com SAPI5 no Windows
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", app_config.audio.tts_rate)
            engine.setProperty("volume", app_config.audio.tts_volume)
            
            selected_voice = app_config.audio.tts_voice_id
            if selected_voice:
                engine.setProperty("voice", selected_voice)

            engine.say(clean_text)
            engine.runAndWait()
            engine.stop()

        except Exception as e:
            logger.error(f"Erro durante síntese de voz TTS: {e}")
        finally:
            with self._lock:
                self._is_speaking = False
            if on_end:
                try:
                    on_end()
                except Exception:
                    pass

    def stop(self) -> None:
        """Interrompe a fala imediatamente."""
        with self._lock:
            self._is_speaking = False
        try:
            if self._engine is not None:
                self._engine.stop()
        except Exception as e:
            logger.debug(f"Erro ao parar engine TTS: {e}")

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking


local_tts = LocalTTS()
