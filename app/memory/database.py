"""
Gerenciador de Banco de Dados SQLite local do JARVIS.
Cria as tabelas, índices e gerencia conexões seguras com WAL mode.
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from app.core.logging_config import get_logger

logger = get_logger("memory.database")

DB_PATH = Path("data") / "jarvis.db"


class DatabaseManager:
    """Gerenciador de persistência SQLite thread-safe."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._local = threading.local()
        self._lock = threading.Lock()
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """Obtém uma conexão de banco de dados vinculada à thread atual."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # Ativa modo WAL para concorrência superior e chaves estrangeiras
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.conn = conn
        return self._local.conn

    def initialize_database(self) -> None:
        """Cria o esquema inicial de tabelas e índices se não existirem."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = self.get_connection()
            with conn:
                # 1. Tabela de Conversas
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        summary TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        message_count INTEGER DEFAULT 0
                    );
                """)

                # 2. Tabela de Mensagens
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        has_image INTEGER DEFAULT 0,
                        tool_calls_json TEXT,
                        tool_results_json TEXT,
                        created_at REAL NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    );
                """)

                # 3. Tabela de Memórias de Longo Prazo
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        importance INTEGER DEFAULT 3,
                        embedding BLOB,
                        source TEXT DEFAULT 'conversation',
                        tags TEXT,
                        created_at REAL NOT NULL,
                        last_accessed_at REAL NOT NULL,
                        access_count INTEGER DEFAULT 0
                    );
                """)

                # 4. Tabela de Preferências do Usuário
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id TEXT PRIMARY KEY,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        created_at REAL NOT NULL
                    );
                """)

                # 5. Tabela de Lembretes Agendados
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        due_timestamp REAL NOT NULL,
                        is_completed INTEGER DEFAULT 0,
                        is_recurring INTEGER DEFAULT 0,
                        recurrence_rule TEXT,
                        created_at REAL NOT NULL
                    );
                """)

                # 6. Tabela de Notas Rápidas
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    );
                """)

                # 7. Tabela de Histórico de Execução de Ferramentas
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tool_history (
                        id TEXT PRIMARY KEY,
                        tool_name TEXT NOT NULL,
                        arguments_json TEXT,
                        result_json TEXT,
                        status TEXT NOT NULL,
                        duration_ms REAL,
                        created_at REAL NOT NULL
                    );
                """)

                # Índices para performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(due_timestamp, is_completed);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);")

            logger.info("Banco de dados SQLite inicializado com sucesso.")

    def close(self) -> None:
        """Fecha a conexão da thread atual."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None


# Instância global compartilhada
db = DatabaseManager()
