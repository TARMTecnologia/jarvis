"""
Ferramentas de Gerenciamento de Lembretes Locais do JARVIS.
Integradas ao banco SQLite e disparadas pelo agendador do Windows.
"""

import time
import uuid
import datetime
from typing import Dict, Any, List, Optional
from app.tools.registry import tool
from app.tools.permissions import PermissionLevel
from app.memory.database import db
from app.core.logging_config import get_logger

logger = get_logger("tools.reminders")


@tool(
    name="create_reminder",
    description="Cria um lembrete local persistente no computador. Pode especificar minutos a partir de agora (ex: 30) ou horario especifico (ex: '17:30').",
    permission_level=PermissionLevel.SAFE
)
def create_reminder(text: str, minutes_from_now: Optional[int] = None, target_time_str: Optional[str] = None) -> Dict[str, Any]:
    now = datetime.datetime.now()
    due_dt = None

    if minutes_from_now is not None and minutes_from_now > 0:
        due_dt = now + datetime.timedelta(minutes=minutes_from_now)
    elif target_time_str:
        clean_time = target_time_str.strip().replace("h", ":").replace("H", ":")
        try:
            parts = clean_time.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate < now:
                candidate += datetime.timedelta(days=1)
            due_dt = candidate
        except Exception as e:
            logger.warning(f"Formato de hora invalido '{target_time_str}': {e}")
            due_dt = now + datetime.timedelta(minutes=10)
    else:
        due_dt = now + datetime.timedelta(minutes=15)

    due_timestamp = due_dt.timestamp()
    reminder_id = str(uuid.uuid4())

    try:
        conn = db.get_connection()
        with conn:
            conn.execute("""
                INSERT INTO reminders (id, text, due_timestamp, is_completed, is_recurring, created_at)
                VALUES (?, ?, ?, 0, 0, ?)
            """, (reminder_id, text, due_timestamp, time.time()))

        formatted_due = due_dt.strftime("%d/%m/%Y as %H:%M")
        logger.info(f"Lembrete criado: '{text}' para {formatted_due}")

        return {
            "status": "success",
            "reminder_id": reminder_id,
            "text": text,
            "due_time": formatted_due,
            "message": f"Lembrete agendado para {formatted_due}: '{text}'"
        }
    except Exception as e:
        logger.error(f"Erro ao salvar lembrete: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="list_reminders",
    description="Lista todos os lembretes pendentes ou agendados no sistema.",
    permission_level=PermissionLevel.SAFE
)
def list_reminders(include_completed: bool = False) -> Dict[str, Any]:
    try:
        conn = db.get_connection()
        reminders = []

        query = """
            SELECT id, text, due_timestamp, is_completed, created_at
            FROM reminders
        """
        if not include_completed:
            query += " WHERE is_completed = 0 "
        query += " ORDER BY due_timestamp ASC LIMIT 20 "

        cursor = conn.execute(query)
        now_ts = time.time()

        for row in cursor.fetchall():
            due_ts = row["due_timestamp"]
            due_dt = datetime.datetime.fromtimestamp(due_ts)
            reminders.append({
                "id": row["id"],
                "text": row["text"],
                "due_time": due_dt.strftime("%d/%m/%Y %H:%M"),
                "is_completed": bool(row["is_completed"]),
                "is_overdue": due_ts < now_ts and not bool(row["is_completed"])
            })

        return {
            "status": "success",
            "count": len(reminders),
            "reminders": reminders
        }
    except Exception as e:
        logger.error(f"Erro ao listar lembretes: {e}")
        return {"status": "error", "error": str(e)}


@tool(
    name="cancel_reminder",
    description="Cancela ou exclui um lembrete pelo ID ou pelo texto.",
    permission_level=PermissionLevel.SAFE
)
def cancel_reminder(reminder_id_or_text: str) -> Dict[str, Any]:
    target = reminder_id_or_text.strip()
    try:
        conn = db.get_connection()
        with conn:
            cursor = conn.execute("""
                DELETE FROM reminders
                WHERE id = ? OR text LIKE ?
            """, (target, f"%{target}%"))

            if cursor.rowcount > 0:
                return {"status": "success", "message": f"{cursor.rowcount} lembrete(s) cancelado(s) com sucesso."}
            else:
                return {"status": "not_found", "message": f"Nenhum lembrete encontrado com '{target}'."}
    except Exception as e:
        logger.error(f"Erro ao cancelar lembrete: {e}")
        return {"status": "error", "error": str(e)}
