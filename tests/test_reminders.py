"""
Testes Unitarios para o Agendador de Lembretes.
"""

import pytest
import time
from app.tools.reminder_tools import create_reminder, list_reminders, cancel_reminder


def test_create_and_list_reminders():
    # Cria lembrete para daqui a 5 minutos
    res = create_reminder(text="Reuniao com time de IA", minutes_from_now=5)
    assert res["status"] == "success"
    assert "due_time" in res

    # Lista lembretes
    list_res = list_reminders(include_completed=False)
    assert list_res["status"] == "success"
    assert any("Reuniao com time de IA" in r["text"] for r in list_res["reminders"])

    # Cancela lembrete
    cancel_res = cancel_reminder("Reuniao com time de IA")
    assert cancel_res["status"] == "success"
