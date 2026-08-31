"""
Modelos de dados para o sistema de memória e persistência do JARVIS.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import time
import uuid


class MemoryType(str, Enum):
    """Tipos de memória para categorização e busca semântica."""
    SEMANTIC = "semantic"       # Fatos permanentes ("Meu nome é Thiago")
    EPISODIC = "episodic"       # Acontecimentos datados ("Ontem mencionei que estava viajando")
    PREFERENCE = "preference"   # Preferências ("Gosto de respostas diretas")
    FACT = "fact"               # Fatos pontuais ("Meu carro é um Corolla")
    PROJECT = "project"         # Projetos e metas ("Desenvolvendo o software Jarvis")


class MemoryRecord(BaseModel):
    """Registro individual de memória de longo prazo."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    importance: int = Field(default=3, ge=1, le=5, description="Nível de relevância de 1 a 5")
    embedding: Optional[bytes] = None  # Float array serializado em bytes
    source: str = "conversation"
    tags: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    last_accessed_at: float = Field(default_factory=time.time)
    access_count: int = 0


class ConversationRecord(BaseModel):
    """Registro de uma sessão de conversa."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "Nova Conversa"
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    summary: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    message_count: int = 0


class MessageRecord(BaseModel):
    """Mensagem armazenada no histórico de conversas."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str  # "user", "assistant", "system", "tool"
    content: str
    has_image: bool = False
    tool_calls_json: Optional[str] = None
    tool_results_json: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class ReminderRecord(BaseModel):
    """Lembrete local com notificação agendada."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    due_timestamp: float
    is_completed: bool = False
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class NoteRecord(BaseModel):
    """Nota rápida anotada pelo usuário."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class UserPreferenceRecord(BaseModel):
    """Preferência do usuário gravada."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key: str
    value: str
    category: str = "general"
    created_at: float = Field(default_factory=time.time)
