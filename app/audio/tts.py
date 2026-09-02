"""
Motor Hibrido de Sintese de Voz (Text-To-Speech) Ultra-Humanizado, Emocional e Exclusivamente Masculino para o JARVIS.
Filtra automaticamente emojis e tags markdown para garantir que a fala nunca soe robotica ou vocalize emojis.
"""

import asyncio
import io
import re
import threading
import urllib.parse
import urllib.request
import json
from typing import List, Dict, Any, Optional, Callable
import sounddevice
import soundfile
import pythoncom
import pyttsx3
from app.core.config import app_config
from app.security.secrets import secrets_manager
from app.core.logging_config import get_logger

logger = get_logger("audio.tts")

DEFAULT_MALE_NEURAL_VOICE = "pt-BR-AntonioNeural"

# Regex universal para remocao de emojis Unicode e simbolos graficos
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff"
    r"\U00002600-\U000027BF"
    r"\U0001F300-\U0001F64F"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF"
    r"\u200d\ufe0f"
    r"]+",
    flags=re.UNICODE
)


def clean_text_for_speech(text: str) -> str:
    """Remove emojis, tags markdown e caracteres especiais para fala 100% limpa e natural."""
    if not text:
        return ""
    # Remove emojis
    no_emojis = EMOJI_PATTERN.sub("", text)
    # Remove formatacoes markdown como **texto**, `codigo`, # Titulo, [link](...)
    no_markdown = re.sub(r"[*_`#~\[\]\(\)]", "", no_emojis)
    # Remove espacos extras
    cleaned = re.sub(r"\s+", " ", no_markdown).strip()
    return cleaned


class LocalTTS:
    """Motor de síntese de voz 100% masculino, humano e ágil para o JARVIS."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_requested = False

        if not app_config.audio.tts_voice_id or "maria" in app_config.audio.tts_voice_id.lower() or "francisca" in app_config.audio.tts_voice_id.lower():
            app_config.audio.tts_voice_id = DEFAULT_MALE_NEURAL_VOICE
            app_config.save()

    def list_voices(self) -> List[Dict[str, Any]]:
        """Lista vozes masculinas disponiveis (OpenAI Human, Edge-TTS Neural e SAPI5 Local)."""
        male_voices = [
            {"id": "openai:onyx", "name": "JARVIS OpenAI Human — Onyx (Cinema / Ultra-Realista)", "gender": "Masculino"},
            {"id": "openai:echo", "name": "JARVIS OpenAI Human — Echo (Conversacional / Caloroso)", "gender": "Masculino"},
            {"id": "pt-BR-AntonioNeural", "name": "JARVIS Neural — Antonio (Masculino PT-BR Rápido)", "gender": "Masculino"},
            {"id": "pt-BR-FabioNeural", "name": "JARVIS Neural — Fábio (Masculino PT-BR Alternativo)", "gender": "Masculino"},
            {"id": "en-US-GuyNeural", "name": "JARVIS Neural — Guy (Masculino EN-US)", "gender": "Masculino"},
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
        Sintetiza e reproduz o texto com voz humana, expressiva e sem pronunciar emojis.
        """
        clean_text = clean_text_for_speech(text)
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

            played = False

            # 1. Se configurado para OpenAI TTS ou se for voz OpenAI (onyx / echo)
            if selected_voice.startswith("openai:") or getattr(app_config.audio, "tts_engine", "") == "openai_tts":
                voice_name = selected_voice.replace("openai:", "").strip() or "onyx"
                played = self._speak_openai_tts(clean_text, voice_name=voice_name)

            # 2. Se configurado para ElevenLabs
            if not played and getattr(app_config.audio, "tts_engine", "") == "elevenlabs":
                played = self._speak_elevenlabs(clean_text)

            # 3. Fallback ou padrao para Edge-TTS Neural Masculino
            if not played and not self._stop_requested:
                edge_voice = selected_voice if "Neural" in selected_voice else DEFAULT_MALE_NEURAL_VOICE
                played = self._speak_neural(clean_text, edge_voice)

            # 4. Fallback final offline para SAPI5 Local
            if not played and not self._stop_requested:
                logger.info("Tentando fallback para SAPI5 local masculino...")
                self._speak_sapi5(clean_text)

        finally:
            with self._lock:
                self._is_speaking = False

            if on_end:
                try:
                    on_end()
                except Exception:
                    pass

    def _speak_openai_tts(self, text: str, voice_name: str = "onyx") -> bool:
        """Sintetiza voz ultra-humana e cinematografica via OpenAI TTS (tts-1)."""
        openai_key = secrets_manager.get_api_key("openai")
        if not openai_key:
            return False

        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)

            response = client.audio.speech.create(
                model="tts-1",
                voice=voice_name if voice_name in ["onyx", "echo", "alloy", "fable", "shimmer", "nova"] else "onyx",
                input=text,
                speed=1.15
            )

            if self._stop_requested:
                return True

            audio_data = io.BytesIO(response.content)
            data, sr = soundfile.read(audio_data)

            if self._stop_requested:
                return True

            dev_idx = app_config.audio.output_device_index
            sounddevice.play(data, samplerate=sr, device=dev_idx)

            while sounddevice.get_stream() and sounddevice.get_stream().active:
                if self._stop_requested:
                    sounddevice.stop()
                    break
                sounddevice.sleep(20)

            return True

        except Exception as e:
            logger.warning(f"Sintese OpenAI TTS falhou ({e}). Tentando Edge-TTS.")
            return False

    def _speak_elevenlabs(self, text: str, voice_id: str = "pNInz6obpgDQGcFmaJgB") -> bool:
        """Sintetiza via ElevenLabs se a API Key estiver configurada."""
        eleven_key = secrets_manager.get_api_key("elevenlabs")
        if not eleven_key:
            return False

        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": eleven_key
            }
            payload = json.dumps({
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                audio_bytes = response.read()

            if self._stop_requested:
                return True

            data, sr = soundfile.read(io.BytesIO(audio_bytes))
            dev_idx = app_config.audio.output_device_index
            sounddevice.play(data, samplerate=sr, device=dev_idx)

            while sounddevice.get_stream() and sounddevice.get_stream().active:
                if self._stop_requested:
                    sounddevice.stop()
                    break
                sounddevice.sleep(20)

            return True
        except Exception as e:
            logger.warning(f"Sintese ElevenLabs falhou ({e}). Tentando Edge-TTS.")
            return False

    def _speak_neural(self, text: str, voice_name: str) -> bool:
        """Sintetiza voz neural masculina acelerada via Edge-TTS (+35% rate)."""
        try:
            import edge_tts

            async def _generate():
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
