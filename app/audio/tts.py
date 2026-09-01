"""
Motor Hibrido de Sintese de Voz (Text-To-Speech) EXCLUSIVAMENTE MASCULINO para o JARVIS.
Voz neural masculina de alta definicao acelerada (+35% speed) e interrupcao instantanea (<20ms).
"""

import asyncio
import io
import threading
import winreg
from typing import List, Dict, Any, Optional, Callable
import sounddevice
import soundfile
import pythoncom
import pyttsx3
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.tts")

DEFAULT_MALE_NEURAL_VOICE = "pt-BR-AntonioNeural"


class LocalTTS:
    """Motor de síntese de voz 100% masculino e ágil para o JARVIS."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_requested = False

        if not app_config.audio.tts_voice_id or "maria" in app_config.audio.tts_voice_id.lower() or "francisca" in app_config.audio.tts_voice_id.lower():
            app_config.audio.tts_voice_id = DEFAULT_MALE_NEURAL_VOICE
            app_config.save()

    def list_voices(self) -> List[Dict[str, Any]]:
        """Lista EXCLUSIVAMENTE vozes masculinas disponiveis no sistema e neurais."""
        male_voices = [
            {"id": "pt-BR-AntonioNeural", "name": "JARVIS Neural — Antonio (Masculino PT-BR Rápido)", "gender": "Masculino"},
            {"id": "pt-BR-FabioNeural", "name": "JARVIS Neural — Fábio (Masculino PT-BR Alternativo)", "gender": "Masculino"},
            {"id": "en-US-GuyNeural", "name": "JARVIS Neural — Guy (Masculino EN-US)", "gender": "Masculino"},
            {"id": "en-US-ChristopherNeural", "name": "JARVIS Neural — Christopher (Masculino EN-US)", "gender": "Masculino"},
        ]

        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init("sapi5")
            for v in engine.getProperty("voices"):
                vname = v.name.lower()
                vid = v.id.lower()
                if any(m in vname or m in vid for m in ["daniel", "david", "mark", "george", "pablo", "paul", "stefan"]):
                    male_voices.append({
                        "id": v.id,
                        "name": f"{v.name} (Masculino SAPI5 Local)",
                        "gender": "Masculino"
                    })
        except Exception as e:
            logger.debug(f"Aviso ao consultar vozes SAPI5: {e}")
        finally:
            pythoncom.CoUninitialize()

        return male_voices

    def speak(self, text: str, on_start: Optional[Callable[[], None]] = None, on_end: Optional[Callable[[], None]] = None) -> None:
        """
        Sintetiza e reproduz o texto com voz masculina rápida e fluida.
        """
        clean_text = text.strip()
        if not clean_text or app_config.system.silent_mode:
            if on_end:
                on_end()
            return

        with self._lock:
            self._is_speaking = True
            self._stop_requested = False

        if on_start:
            try:
                on_start()
            except Exception:
                pass

        try:
            selected_voice = app_config.audio.tts_voice_id or DEFAULT_MALE_NEURAL_VOICE
            if "maria" in selected_voice.lower() or "francisca" in selected_voice.lower():
                selected_voice = DEFAULT_MALE_NEURAL_VOICE

            if "Neural" in selected_voice or "pt-BR" in selected_voice:
                success = self._speak_neural(clean_text, selected_voice)
                if not success and not self._stop_requested:
                    logger.info("Tentando fallback para SAPI5 local masculino...")
                    self._speak_sapi5(clean_text)
            else:
                self._speak_sapi5(clean_text, selected_voice)
        finally:
            with self._lock:
                self._is_speaking = False

            if on_end:
                try:
                    on_end()
                except Exception:
                    pass

    def _speak_neural(self, text: str, voice_name: str) -> bool:
        """Sintetiza voz neural masculina acelerada via Edge-TTS (+35% rate)."""
        try:
            import edge_tts

            async def _generate():
                # Acelera a fala em +35% para um ritmo rápido, inteligente e moderno
                communicate = edge_tts.Communicate(text, voice_name, rate="+35%")
                audio_buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if self._stop_requested:
                        return None
                    if chunk["type"] == "audio":
                        audio_buffer.write(chunk["data"])
                audio_buffer.seek(0)
                return audio_buffer

            loop = asyncio.new_event_loop()
            buf = loop.run_until_complete(_generate())
            loop.close()

            if buf is None or self._stop_requested:
                return True

            data, sr = soundfile.read(buf)
            if self._stop_requested:
                return True

            dev_idx = app_config.audio.output_device_index
            sounddevice.play(data, samplerate=sr, device=dev_idx)
            
            # Loop de reprodução com checagem de parada a cada 20ms para parada instantânea
            while sounddevice.get_stream() and sounddevice.get_stream().active:
                if self._stop_requested:
                    sounddevice.stop()
                    break
                sounddevice.sleep(20)

            return True

        except Exception as e:
            logger.warning(f"Sintese neural falhou ({e}). Ativando fallback SAPI5.")
            return False

    def _speak_sapi5(self, text: str, voice_id: Optional[str] = None) -> None:
        """Fallback offline nativo masculino via Windows SAPI5 (taxa acelerada 240 wpm)."""
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", 240)
            engine.setProperty("volume", app_config.audio.tts_volume or 1.0)

            if voice_id and "HKEY" in voice_id:
                try:
                    engine.setProperty("voice", voice_id)
                except Exception:
                    pass

            engine.say(text)
            engine.runAndWait()
            engine.stop()

        except Exception as e:
            logger.error(f"Erro no fallback SAPI5: {e}")
        finally:
            pythoncom.CoUninitialize()

    def stop(self) -> None:
        """Interrompe a fala no mesmo instante (<20ms)."""
        with self._lock:
            self._stop_requested = True
            self._is_speaking = False
        try:
            sounddevice.stop()
        except Exception:
            pass

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking


local_tts = LocalTTS()
