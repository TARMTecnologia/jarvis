"""
Registro Universal de Ferramentas do JARVIS.
Permite definir e catalogar funcoes acessiveis a IA atraves de decorators (@tool).
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
import inspect
from app.tools.permissions import PermissionLevel
from app.core.logging_config import get_logger

logger = get_logger("tools.registry")


@dataclass
class ToolMetadata:
    """Metadados e definicao de uma ferramenta."""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any]
    permission_level: PermissionLevel = PermissionLevel.SAFE


class ToolRegistry:
    """Catalogo central de ferramentas executaveis."""

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        permission_level: PermissionLevel = PermissionLevel.SAFE
    ) -> Callable:
        """Decorator para registrar uma funcao como ferramenta da IA."""
        def decorator(func: Callable) -> Callable:
            params_schema = parameters or self._infer_parameters(func)
            meta = ToolMetadata(
                name=name,
                description=description,
                func=func,
                parameters=params_schema,
                permission_level=permission_level
            )
            self._tools[name] = meta
            logger.debug(f"Ferramenta registrada: '{name}' [{permission_level.value}]")
            return func
        return decorator

    def _infer_parameters(self, func: Callable) -> Dict[str, Any]:
        """Gera um JSON Schema a partir da assinatura da funcao."""
        sig = inspect.signature(func)
        properties: Dict[str, Any] = {}
        required: List[str] = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }

        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                param_type = type_map.get(param.annotation, "string")

            properties[name] = {
                "type": param_type,
                "description": f"Parametro {name}"
            }

            if param.default == inspect.Parameter.empty:
                required.append(name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Recupera metadados da ferramenta pelo nome."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolMetadata]:
        """Retorna lista de todas as ferramentas cadastradas."""
        return list(self._tools.values())

    def get_schemas_for_ai(self) -> List[Dict[str, Any]]:
        """Exporta a lista de esquemas em formato universal JSON Schema."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            })
        return schemas


# Instancia global compartilhada
tool_registry = ToolRegistry()
tool = tool_registry.register
