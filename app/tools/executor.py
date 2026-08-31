"""
Executor Seguro e Assincrono de Ferramentas.
Gerencia chamadas, valida permissoes, trata excecoes e grava historico no SQLite.
"""

import asyncio
import inspect
import json
import time
import uuid
from typing import Dict, Any, Tuple
from app.tools.registry import tool_registry, ToolMetadata
from app.tools.permissions import permission_manager, PermissionLevel
from app.memory.database import db
from app.core.logging_config import get_logger

logger = get_logger("tools.executor")


class ToolExecutor:
    """Executor centralizado de ferramentas com sandbox de seguranca."""

    @staticmethod
    async def execute(name: str, arguments: Dict[str, Any], timeout_seconds: float = 15.0) -> Dict[str, Any]:
        """
        Executa a ferramenta solicitada com controle de permissao e timeout.
        Retorna dicionario com status, resultado ou erro.
        """
        tool_meta = tool_registry.get_tool(name)
        if not tool_meta:
            err_msg = f"Ferramenta '{name}' nao encontrada no registro do JARVIS."
            logger.warning(err_msg)
            return {"status": "error", "error": err_msg}

        # 1. Validacao de Permissoes
        allowed, perm_msg = permission_manager.check_permission(
            tool_name=name,
            level=tool_meta.permission_level,
            args=arguments
        )

        if not allowed:
            logger.warning(f"Execucao da ferramenta '{name}' bloqueada: {perm_msg}")
            return {
                "status": "denied",
                "error": f"Execucao da acao '{name}' nao foi autorizada: {perm_msg}"
            }

        # 2. Execucao protegida
        start_time = time.time()
        result_payload = None
        status = "success"
        error_msg = None

        try:
            logger.info(f"Executando ferramenta: '{name}' com argumentos: {arguments}")
            
            if inspect.iscoroutinefunction(tool_meta.func):
                result_payload = await asyncio.wait_for(
                    tool_meta.func(**arguments),
                    timeout=timeout_seconds
                )
            else:
                result_payload = await asyncio.wait_for(
                    asyncio.to_thread(tool_meta.func, **arguments),
                    timeout=timeout_seconds
                )

        except asyncio.TimeoutError:
            status = "timeout"
            error_msg = f"Tempo limite de execucao excedido ({timeout_seconds}s) para a ferramenta '{name}'."
            logger.error(error_msg)
        except TypeError as te:
            status = "error"
            error_msg = f"Argumentos invalidos para a ferramenta '{name}': {str(te)}"
            logger.error(error_msg)
        except Exception as e:
            status = "error"
            error_msg = f"Erro ao executar '{name}': {str(e)}"
            logger.error(error_msg, exc_info=True)

        duration_ms = (time.time() - start_time) * 1000

        # 3. Registro no historico de execucao (SQLite)
        try:
            conn = db.get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO tool_history (id, tool_name, arguments_json, result_json, status, duration_ms, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    name,
                    json.dumps(arguments, ensure_ascii=False),
                    json.dumps(result_payload if result_payload is not None else {"error": error_msg}, ensure_ascii=False),
                    status,
                    duration_ms,
                    time.time()
                ))
        except Exception as log_err:
            logger.warning(f"Erro ao salvar historico de ferramenta no SQLite: {log_err}")

        if status == "success":
            return {"status": "success", "result": result_payload, "duration_ms": duration_ms}
        else:
            return {"status": status, "error": error_msg, "duration_ms": duration_ms}


tool_executor = ToolExecutor()
