"""MCP substrate — a thin, standards-aligned registry for external integrations.

The Nova OS standardizes connectors/tools on the Model Context Protocol shape: every
integration is a named Tool with a JSON-schema input and a callable. Apps register tools
here; the connector framework + agents discover them uniformly, so adding a source/tool
is a registration, not a bespoke bridge. (Pure stdlib; the wire-level MCP server/client
is layered on top later — this is the in-process contract.)
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict = field(default_factory=dict)   # JSON Schema
    handler: Callable | None = None                     # callable(**kwargs) -> result
    consent_kind: str = "read"                           # maps to consent.DEFAULTS for WARDEN
    privacy_default: str = "semi"                         # default privacy tier of its output


class Registry:
    """In-process tool registry. One per app; future: federate over the mesh."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def manifest(self) -> list[dict]:
        """MCP-style discovery manifest (name/description/input_schema)."""
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in self._tools.values()
        ]


registry = Registry()
