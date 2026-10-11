"""Tool Registry for ORCA Agent 6: AI Workspace Assistant.

Provides modular tool definitions, validation, controlled execution,
and permission enforcement.
"""

from dataclasses import dataclass, field
import inspect
import time
from typing import Any, Awaitable, Callable


@dataclass
class ToolDefinition:
    """Specification of an executable assistant tool."""

    name: str
    description: str
    category: str  # "specialist", "system", "workspace"
    parameters: dict[str, Any]
    handler: Callable[..., Awaitable[Any] | Any]
    requires_approval: bool = False
    read_only: bool = True


class ToolRegistry:
    """Registry managing available tools, schemas, and safe execution."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool definition."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with metadata."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": t.parameters,
                "requires_approval": t.requires_approval,
                "read_only": t.read_only,
            }
            for t in self._tools.values()
        ]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        approved: bool = False,
    ) -> dict[str, Any]:
        """Execute a tool with parameter validation and timing."""
        tool = self.get(name)
        if not tool:
            return {
                "success": False,
                "output": None,
                "error": f"Tool '{name}' is not registered in the assistant tool registry.",
                "duration_ms": 0.0,
            }

        if tool.requires_approval and not approved:
            return {
                "success": False,
                "output": None,
                "error": f"Tool '{name}' requires explicit user authorization before execution.",
                "requires_approval": True,
                "duration_ms": 0.0,
            }

        start_time = time.perf_counter()
        try:
            handler = tool.handler
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            duration = round((time.perf_counter() - start_time) * 1000.0, 2)
            return {
                "success": True,
                "output": result,
                "error": None,
                "duration_ms": duration,
            }
        except TypeError as exc:
            duration = round((time.perf_counter() - start_time) * 1000.0, 2)
            return {
                "success": False,
                "output": None,
                "error": f"Invalid arguments for tool '{name}': {str(exc)}",
                "duration_ms": duration,
            }
        except Exception as exc:
            duration = round((time.perf_counter() - start_time) * 1000.0, 2)
            return {
                "success": False,
                "output": None,
                "error": f"Tool '{name}' execution failed: {type(exc).__name__}: {str(exc)}",
                "duration_ms": duration,
            }
