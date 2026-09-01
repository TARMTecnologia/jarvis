"""
Gerenciamento de configuracoes do assistente JARVIS.
Permite personalizacao de IA, Audio, Camera, Memoria e Sistema.
"""

import json
import os
from pathlib import Path
from typing import Literal, Optional, List
from pydantic import BaseModel, Field
from app.core.logging_config import get_logger

logger = get_logger("core.config")

CONFIG_FILE_PATH = Path("data") / "config.json"

# Provedores e modelos recomendados oficialmente
RECOMMENDED_MODELS = {
    "openai": {
        "default": "gpt-4o",
        "recommended": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-5",
            "gpt-4.5-preview",
            "o3-mini",
            "o1",
            "o1-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ],
        "realtime": "gpt-4o-realtime-preview"
    },
    "gemini": {
        "default": "gemini-2.0-flash",
        "recommended": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ],
        "realtime": "gemini-2.0-flash"
    },
    "anthropic": {
        "default": "claude-3-5-sonnet-20241022",
        "recommended": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229"
        ],
        "realtime": None
    },
    "claude": {
        "default": "claude-3-5-sonnet-20241022",
        "recommended": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ],
        "realtime": None
    }
}


class AISettings(BaseModel):
    """Configuracoes da Inteligencia Artificial."""
    provider: Literal["openai", "gemini", "anthropic", "claude"] = Field(
        default="openai", description="Provedor ativo de IA"
    )
    model: str = Field(default="gpt-4o", description="ID do modelo a ser utilizado")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=100, le=8192)
    use_realtime_api: bool = Field(default=True, description="Usar Realtime API quando suportado")
    system_prompt_override: Optional[str] = Field(default=None, description="Prompt de sistema personalizado")


class AudioSettings(BaseModel):
    """Configuracoes de Audio, Voz, STT e TTS."""
    input_device_index: Optional[int] = Field(default=None, description="Indice do microfone")
    output_device_index: Optional[int] = Field(default=None, description="Indice do alto-falante")
    voice_mode: Literal["wakeword", "continuous", "push_to_talk"] = Field(
        default="wakeword", description="Modo de ativacao por voz"
    )
    wake_word: str = Field(default="Jarvis", description="Palavra de ativacao")
    vad_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0, description="Sensibilidade de deteccao de voz")
    silence_threshold_ms: int = Field(default=1200, ge=400, le=3000, description="Tempo de silencio para fim de fala")
    stt_engine: Literal["local_whisper", "openai_whisper"] = Field(
        default="local_whisper", description="Motor de transcricao de fala (Local ou OpenAI Cloud)"
    )
    stt_model_size: str = Field(default="base", description="Tamanho do modelo Whisper local (tiny, base, small, medium)")
    tts_engine: Literal["sapi5", "piper"] = Field(default="sapi5", description="Motor de sintese de voz local")
    tts_voice_id: Optional[str] = Field(default=None, description="ID da voz TTS selecionada")
    tts_rate: int = Field(default=190, ge=100, le=300, description="Velocidade da fala (palavras por minuto)")
    tts_volume: float = Field(default=1.0, ge=0.0, le=1.0, description="Volume da fala")
    barge_in_enabled: bool = Field(default=True, description="Permitir interromper fala do Jarvis")
    mentor_voice_filter_enabled: bool = Field(default=False, description="Filtrar e aceitar apenas a voz calibrada do mentor")
    mentor_voice_similarity_threshold: float = Field(default=0.55, ge=0.2, le=0.95, description="Limiar de similaridade vocal")


class VisionSettings(BaseModel):
    """Configuracoes de Camera e Visao Computacional."""
    camera_index: int = Field(default=0, description="Indice da camera")
    enabled: bool = Field(default=True, description="Camera habilitada")
    preview_fps: int = Field(default=24, ge=5, le=60, description="Taxa de quadros do preview na UI")
    ai_vision_fps: float = Field(default=0.5, ge=0.0, le=5.0, description="Taxa maxima de envio de frames para IA")
    resolution_width: int = Field(default=640, ge=320, le=1920)
    resolution_height: int = Field(default=480, ge=240, le=1080)
    jpeg_quality: int = Field(default=75, ge=30, le=100, description="Qualidade de compressao JPEG para envio")
    scene_change_threshold: float = Field(default=0.15, ge=0.01, le=1.0, description="Sensibilidade de alteracao de cena")
    smart_scene_sampling: bool = Field(default=True, description="Apenas enviar frames quando houver mudanca visual")


class MemorySettings(BaseModel):
    """Configuracoes de Memoria Persistente e Semantica."""
    enabled: bool = Field(default=True, description="Memoria persistente habilitada")
    max_retrieval_count: int = Field(default=5, ge=1, le=20, description="Top-k memorias recuperadas por turno")
    similarity_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="Limiar minimo de similaridade")
    consolidation_turn_interval: int = Field(default=6, ge=2, le=30, description="Turnos para consolidacao automatica")
    private_mode: bool = Field(default=False, description="Modo privado: nenhuma memoria persistente e salva")

    @property
    def max_retrieval_results(self) -> int:
        return self.max_retrieval_count



class SystemSettings(BaseModel):
    """Configuracoes gerais do sistema e interface."""
    user_name: str = Field(default="Senhor", description="Nome como o assistente deve chamar o mentor")
    assistant_name: str = Field(default="JARVIS", description="Nome do assistente")
    language: str = Field(default="pt-BR", description="Idioma padrao")
    dark_theme: bool = Field(default=True, description="Tema escuro HUD")
    start_with_windows: bool = Field(default=False, description="Iniciar automaticamente com o Windows")
    minimize_to_tray: bool = Field(default=True, description="Minimizar para a bandeja ao fechar janela")
    global_hotkey: str = Field(default="Ctrl+Shift+J", description="Atalho global para invocar Jarvis")
    silent_mode: bool = Field(default=False, description="Modo silencioso (apenas texto, sem TTS)")
    allow_computer_automation: bool = Field(default=False, description="Permitir controle automatizado de mouse/teclado")
    first_run_completed: bool = Field(default=False, description="Se o assistente inicial ja foi executado")


class AppConfig(BaseModel):
    """Configuracao Global da Aplicacao JARVIS."""
    ai: AISettings = Field(default_factory=AISettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    vision: VisionSettings = Field(default_factory=VisionSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    system: SystemSettings = Field(default_factory=SystemSettings)

    @classmethod
    def load(cls) -> "AppConfig":
        """Carrega a configuracao do arquivo JSON ou retorna padrao."""
        if CONFIG_FILE_PATH.exists():
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = cls(**data)
                logger.info("Configuracao carregada com sucesso do arquivo.")
                return config
            except Exception as e:
                logger.error(f"Erro ao carregar {CONFIG_FILE_PATH}, usando padroes: {e}")

        config = cls()
        config.save()
        return config

    def save(self) -> bool:
        """Persiste as configuracoes atuais no arquivo JSON."""
        try:
            CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)
            logger.info("Configuracao salva com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Falha ao salvar configuracao: {e}")
            return False

    def get_default_model_for_provider(self, provider: str) -> str:
        """Retorna o modelo padrao recomendado para o provedor informado."""
        provider_clean = provider.strip().lower()
        info = RECOMMENDED_MODELS.get(provider_clean)
        if info:
            return info["default"]
        return "gpt-4o"


# Instancia global compartilhada
app_config = AppConfig.load()
