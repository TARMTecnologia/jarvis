"""
Sintese de Voz Local (Text-To-Speech) para o JARVIS.
Utiliza a engine nativa SAPI5 e OneCore do Windows com suporte a vozes masculinas (Microsoft Daniel) e inicializacao COM por thread.
"""

import threading
import winreg
from typing import List, Dict, Any, Optional, Callable
import pyttsx3
import pythoncom
from app.core.config import app_config
from app.core.logging_config import get_logger

logger = get_logger("audio.tts")

DANIEL_MALE_VOICE_TOKEN = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens\MSTTS_V110_ptBR_DanielM"


class LocalTTS:
    """Motor de síntese de voz local nativo do Windows com suporte a vozes masculinas e femininas."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._default_male_voice_id = None
        self._discover_voices()

    def _discover_voices(self) -> None:
        """Descobre vozes SAPI5 e OneCore instaladas no Windows."""
        voices = self.list_voices()
        # Procura primeiro por Daniel (Masculino PT-BR)
        for v in voices:
            vid = v["id"].lower()
            vname = v["name"].lower()
            if "daniel" in vname or "daniel" in vid:
                self._default_male_voice_id = v["id"]
                break
        
        # Se não achou Daniel, procura qualquer voz masculina ou em português
        if not self._default_male_voice_id:
            for v in voices:
                vname = v["name"].lower()
                if "portuguese" in vname or "brazil" in vname:
                    self._default_male_voice_id = v["id"]
                    break

        # Se ainda não estiver configurado no config, define o padrão
        if not app_config.audio.tts_voice_id and self._default_male_voice_id:
            app_config.audio.tts_voice_id = self._default_male_voice_id
            app_config.save()
            logger.info(f"Voz masculina padrão configurada para o JARVIS: {self._default_male_voice_id}")

    def list_voices(self) -> List[Dict[str, Any]]:
        """Lista todas as vozes SAPI5 e OneCore instaladas no Windows."""
        voice_list = []
        seen_ids = set()

        # 1. Busca vozes OneCore no Registro do Windows
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens")
            num_subkeys = winreg.QueryInfoKey(k)[0]
            for i in range(num_subkeys):
                subkey_name = winreg.EnumKey(k, i)
                sub = winreg.OpenKey(k, subkey_name)
                desc = winreg.QueryValue(sub, "")
                token_id = rf"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens\{subkey_name}"
                gender = "Masculino" if any(x in subkey_name.lower() or x in desc.lower() for x in ["daniel", "david", "mark", "pablo", "paul", "adam", "stefan", "andrei", "pavel", "jakub", "naayf"]) else "Feminino"
                if token_id not in seen_ids:
                    seen_ids.add(token_id)
                    voice_list.append({
                        "id": token_id,
                        "name": f"{desc} ({gender} - OneCore)",
                        "gender": gender
                    })
        except Exception as e:
            logger.debug(f"Aviso ao consultar vozes OneCore no registro: {e}")

        # 2. Busca vozes SAPI5 padrão via pyttsx3
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init("sapi5")
            sapi_voices = engine.getProperty("voices")
            for v in sapi_voices:
                if v.id not in seen_ids:
                    seen_ids.add(v.id)
                    gender = "Masculino" if "david" in v.name.lower() or "daniel" in v.name.lower() else "Feminino"
                    voice_list.append({
                        "id": v.id,
                        "name": f"{v.name} ({gender})",
                        "gender": gender
                    })
        except Exception as e:
            logger.debug(f"Aviso ao consultar vozes SAPI5: {e}")
        finally:
            pythoncom.CoUninitialize()

        return voice_list

    def speak(self, text: str, on_start: Optional[Callable[[], None]] = None, on_end: Optional[Callable[[], None]] = None) -> None:
        """
        Sintetiza e fala o texto com voz masculina e inicialização COM por thread.
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

        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", app_config.audio.tts_rate or 190)
            engine.setProperty("volume", app_config.audio.tts_volume or 1.0)

            selected_voice = app_config.audio.tts_voice_id or self._default_male_voice_id or DANIEL_MALE_VOICE_TOKEN
            if selected_voice:
                try:
                    engine.setProperty("voice", selected_voice)
                except Exception as ve:
                    logger.warning(f"Não foi possível aplicar a voz {selected_voice}: {ve}")

            engine.say(clean_text)
            engine.runAndWait()
            engine.stop()

        except Exception as e:
            logger.error(f"Erro durante síntese de voz TTS: {e}")
        finally:
            pythoncom.CoUninitialize()
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

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking


local_tts = LocalTTS()
