"""
Ferramentas de Gerenciamento de Notas Locais do JARVIS integradas ao SQLite.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.memory.database import db
from app.core.logging_config import get_logger

logger = get_logger("tools.notes")


@tool(
    name="create_note",
    description="Cria e salva uma nota rapida de texto com titulo e conteudo no banco local do JARVIS.",
    permission_level=PermissionLevel.SAFE
)
def create_note(title: str, content: str, tags: Optional[str] = None) -> Dict[str, Any]:
    note_id = str(uuid.uuid4())
    now = time.time()
    tags_str = tags or ""

    try:
        conn = db.get_connection()
        with conn:
            conn.execute("""
                INSERT INTO notes (id, title, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (note_id, title, content, tags_str, now, now))

        logger.info(f"Nota criada: '{title}' (ID: {note_id})")
        return {
            "status": "success",
            "note_id": note_id,
            "title": title,
            "message": f"Nota '{title}' salva com sucesso."
        }
    except Exception as e:
        logger.error(f"Erro ao criar nota: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="read_notes",
    description="Lista ou pesquisa notas salvas pelo titulo ou conteudo.",
    permission_level=PermissionLevel.SAFE
)
def read_notes(search_query: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    try:
        conn = db.get_connection()
        notes = []

        if search_query:
            pattern = f"%{search_query.strip()}%"
            cursor = conn.execute("""
                SELECT id, title, content, tags, created_at, updated_at
                FROM notes
                WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (pattern, pattern, pattern, limit))
        else:
            cursor = conn.execute("""
                SELECT id, title, content, tags, created_at, updated_at
                FROM notes
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))

        for row in cursor.fetchall():
            notes.append({
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "tags": row["tags"],
                "created_at": time.strftime("%d/%m/%Y %H:%M", time.localtime(row["created_at"]))
            })

        return {
            "status": "success",
            "total_found": len(notes),
            "notes": notes
        }
    except Exception as e:
        logger.error(f"Erro ao ler notas: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="delete_note",
    description="Exclui uma nota salva pelo seu ID ou pelo titulo exato.",
    permission_level=PermissionLevel.SENSITIVE
)
def delete_note(note_id_or_title: str) -> Dict[str, Any]:
    target = note_id_or_title.strip()
    try:
        conn = db.get_connection()
        with conn:
            cursor = conn.execute("""
                DELETE FROM notes
                WHERE id = ? OR title = ?
            """, (target, target))

            if cursor.rowcount > 0:
                return {"status": "success", "message": f"Nota '{target}' excluida com sucesso."}
            else:
                return {"status": "not_found", "message": f"Nenhuma nota encontrada com ID ou titulo '{target}'."}
    except Exception as e:
        logger.error(f"Erro ao excluir nota: {e}")
        return {"status": "error", "error": str(e)}
