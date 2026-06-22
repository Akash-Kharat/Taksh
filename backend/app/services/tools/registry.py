"""
Tool Registry (MS-10)

A singleton registry that holds all registered tool instances and provides
fast lookup by name, category, and capability level.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Type

from app.services.tools.base import BaseTool, ToolCategory, CapabilityLevel


class ToolRegistry:
    """
    Central store for all available tools.

    Usage
    -----
    registry = ToolRegistry()
    registry.register(MyTool)          # register a class
    tool = registry.get("my_tool")     # retrieve an instance
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}  # name -> instance

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool_class: Type[BaseTool]) -> None:
        """Instantiate and register a tool class. Raises on duplicate name."""
        instance = tool_class()
        name = instance.definition.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = instance

    def register_all(self, *tool_classes: Type[BaseTool]) -> None:
        for cls in tool_classes:
            self.register(cls)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_all(self) -> List[BaseTool]:
        return list(self._tools.values())

    def list_by_category(self, category: ToolCategory) -> List[BaseTool]:
        return [t for t in self._tools.values() if t.definition.category == category]

    def list_by_capability(self, level: CapabilityLevel) -> List[BaseTool]:
        return [t for t in self._tools.values() if t.definition.capability_level == level]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def category_stats(self) -> Dict[str, int]:
        """Return tool count per category."""
        stats: Dict[str, int] = {}
        for tool in self._tools.values():
            key = tool.definition.category.value
            stats[key] = stats.get(key, 0) + 1
        return stats

    def total(self) -> int:
        return len(self._tools)

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    def exists(self, name: str) -> bool:
        return name in self._tools
