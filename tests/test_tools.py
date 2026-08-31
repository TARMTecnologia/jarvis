"""
Testes Unitarios para o Modulo de Ferramentas e Permissoes.
"""

import pytest
from app.tools.registry import tool_registry
from app.tools.permissions import permission_manager, PermissionLevel
from app.tools.executor import tool_executor
import app.tools.system_tools
import app.tools.note_tools


def test_tool_registration():
    time_tool = tool_registry.get_tool("get_current_time")
    assert time_tool is not None
    assert time_tool.permission_level == PermissionLevel.SAFE
    assert "horario" in time_tool.description.lower() or "hora" in time_tool.description.lower()


def test_permissions_check():
    # SAFE deve passar automaticamente
    allowed, msg = permission_manager.check_permission("get_current_time", PermissionLevel.SAFE, {})
    assert allowed is True

    # DESTRUCTIVE sem handler deve ser bloqueado
    allowed_dest, msg_dest = permission_manager.check_permission("shutdown_computer", PermissionLevel.DESTRUCTIVE, {})
    assert allowed_dest is False


@pytest.mark.asyncio
async def test_tool_executor_safe_execution():
    result = await tool_executor.execute("get_current_time", {})
    assert result["status"] == "success"
    assert "time" in result["result"]
    assert "formatted" in result["result"]


@pytest.mark.asyncio
async def test_note_tool_creation_and_reading():
    create_res = await tool_executor.execute("create_note", {
        "title": "Nota de Teste Pytest",
        "content": "Conteudo da nota automatizada"
    })
    assert create_res["status"] == "success"

    read_res = await tool_executor.execute("read_notes", {"search_query": "Pytest"})
    assert read_res["status"] == "success"
    assert len(read_res["result"]["notes"]) >= 1
