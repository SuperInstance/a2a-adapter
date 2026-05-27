"""AdapterRegistry — discovering and loading adapters by protocol."""

from __future__ import annotations

from typing import Dict, List, Optional

from .adapter import Adapter


class AdapterRegistry:
    """
    Central registry for adapter instances.

    Adapters are registered by name and can be looked up by name or
    by their declared ``target_protocol``.
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, Adapter] = {}

    # ── Registration ───────────────────────────────────────────

    def register(self, adapter: Adapter) -> None:
        """Register an adapter. Overwrites if name already exists."""
        self._adapters[adapter.name] = adapter

    def unregister(self, name: str) -> None:
        """Remove a registered adapter. Raises KeyError if not found."""
        if name not in self._adapters:
            raise KeyError(f"No adapter registered as '{name}'")
        del self._adapters[name]

    # ── Lookup ─────────────────────────────────────────────────

    def get(self, name: str) -> Adapter:
        """Get an adapter by name. Raises KeyError if not found."""
        if name not in self._adapters:
            raise KeyError(f"No adapter registered as '{name}'")
        return self._adapters[name]

    def find_by_protocol(self, protocol: str) -> List[Adapter]:
        """Return all adapters whose ``target_protocol`` matches."""
        return [
            a for a in self._adapters.values() if a.target_protocol == protocol
        ]

    def find_by_source(self, protocol: str) -> List[Adapter]:
        """Return all adapters whose ``source_protocol`` matches."""
        return [
            a for a in self._adapters.values() if a.source_protocol == protocol
        ]

    # ── Enumeration ────────────────────────────────────────────

    def list_names(self) -> List[str]:
        """Return all registered adapter names."""
        return list(self._adapters.keys())

    def list_all(self) -> List[Adapter]:
        """Return all registered adapters."""
        return list(self._adapters.values())

    def __len__(self) -> int:
        return len(self._adapters)

    def __contains__(self, name: str) -> bool:
        return name in self._adapters
