"""
Motor Hibrido de Sintese de Voz (Text-To-Speech) para o JARVIS.
Utiliza vozes neurais de alta definicao (Edge-TTS Masculino pt-BR-Antonio / pt-BR-Fabio) com fallback offline para SAPI5.
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

DEFAULT_NEURAL_MALE_VOICE = "pt-BR-AntonioNeural"


class LocalTTS:
    """Motor de síntese de voz com suporte a voz neural masculina e fallback offline nativo."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_requested = False
        self._current_stream = None

    def list_voices(self) -> List[Dict[str, Any]]:
        """Lista todas as vozes neurais e nativas disponiveis."""
        voices = [
            {"id": "pt-BR-AntonioNeural", "name": "JARVIS Neural Masculino (Antonio - PT-BR)", "gender": "Masculino"},
            {"id": "pt-BR-FabioNeural", "name": "JARVIS Neural Masculino (Fábio - PT-BR)", "gender": "Masculino"},
            {"id": "pt-BR-FranciscaNeural", "name": "JARVIS Neural Feminino (Francisca - PT-BR)", "gender": "Feminino"},
            {"id": "en-US-GuyNeural", "name": "JARVIS Neural Masculino (Guy - EN-US)", "gender": "Masculino"},
            {"id": "en-US-ChristopherNeural", "name": "JARVIS Neural Masculino (Christopher - EN-US)", "gender": "Masculino"},
        ]

        # Adiciona vozes locais do Windows SAPI5
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init("sapi5")
            for v in engine.getProperty("voices"):
                gender = "Masculino" if "david" in v.name.lower() or "daniel" in v.name.lower() else "Feminino"
                voices.append({
                    "id": v.id,
                    "name": f"{v.name} (SAPI5 Local)",
                    "gender": gender
                })
        except Exception as e:
            logger.debug(f"Aviso ao consultar vozes SAPI5: {e}")
        finally:
            pythoncom.CoUninitialize()

        return voices

    def speak(self, text: str, on_start: Optional[Callable[[], None]] = None, on_end: Optional[Callable[[], None]] = None) -> None:
        """
        Sintetiza e reproduz o texto com voz masculina.
        Tenta primeiro síntese neural; se falhar ou offline, usa SAPI5.
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

        selected_voice = app_config.audio.tts_voice_id or DEFAULT_NEURAL_MALE_VOICE
        # Se o ID configurado for uma voz neural (ou padrao)
        if "Neural" in selected_voice or "pt-BR" in selected_voice:
            success = self._speak_neural(clean_text, selected_voice)
            if not success and not self._stop_requested:
                logger.info("Tentando fallback para SAPI5 local...")
                self._speak_sapi5(clean_text)
        else:
            self._speak_sapi5(clean_text, selected_voice)

        with self._lock:
            self._is_speaking = False

        if on_end:
            try:
                on_end()
            except Exception:
                pass

    def _speak_neural(self, text: str, voice_name: str) -> bool:
        """Sintetiza voz neural de alta definicao via Edge-TTS."""
        try:
            import edge_tts

            async def _generate():
                communicate = edge_tts.Communicate(text, voice_name)
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

            # Reproduz no dispositivo de audio configurado
            dev_idx = app_config.audio.output_device_index
            sounddevice.play(data, samplerate=sr, device=dev_idx)
            
            # Aguarda termino respeitando interrupcao
            while sounddevice.get_stream() and sounddevice.get_stream().active:
                if self._stop_requested:
                    sounddevice.stop()
                    break
                sounddevice.sleep(30)

            return True

        except Exception as e:
            logger.warning(f"Sintese neural falhou ({e}). Ativando fallback SAPI5.")
            return False

    def _speak_sapi5(self, text: str, voice_id: Optional[str] = None) -> None:
        """Fallback offline nativo via Windows SAPI5."""
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", app_config.audio.tts_rate or 190)
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
        """Interrompe a fala imediatamente."""
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
