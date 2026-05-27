"""ProtocolBridge — connecting heterogeneous agent systems."""

from __future__ import annotations

from typing import Dict, List, Optional
from .models import A2ATask, I2IBottle, AgentCard
from .adapter import Adapter
from .transform import MessageTransformer
from .validator import MessageValidator, ValidationError
from .registry import AdapterRegistry


class ProtocolBridge:
    """
    Orchestrates message translation between different agent protocols.

    Usage::

        bridge = ProtocolBridge()
        bridge.register("i2i_a2a", I2IA2AAdapter())

        # Route a bottle to the A2A world
        task = bridge.route_bottle(bottle, target_protocol="a2a")

        # Route a task back to I2I
        bottle = bridge.route_task(task, target_protocol="i2i")
    """

    def __init__(
        self,
        registry: Optional[AdapterRegistry] = None,
        default_validator: Optional[MessageValidator] = None,
    ) -> None:
        self.registry = registry or AdapterRegistry()
        self.validator = default_validator or MessageValidator()
        self._transformer = MessageTransformer()

    # ── Adapter management ─────────────────────────────────────

    def register_adapter(self, adapter: Adapter) -> None:
        """Register an adapter by its name."""
        self.registry.register(adapter)

    def get_adapter(self, name: str) -> Adapter:
        """Retrieve a registered adapter by name."""
        return self.registry.get(name)

    def list_adapters(self) -> List[str]:
        """Return names of all registered adapters."""
        return self.registry.list_names()

    # ── Routing ────────────────────────────────────────────────

    def route_bottle(
        self,
        bottle: I2IBottle,
        target_protocol: str = "a2a",
        adapter_name: Optional[str] = None,
    ) -> A2ATask:
        """
        Route an I2I Bottle through the appropriate adapter to produce
        an A2A Task for *target_protocol*.
        """
        self.validator.validate_bottle(bottle)
        adapter = self._resolve_adapter(adapter_name, bottle, target_protocol)
        return adapter.send_bottle(bottle)

    def route_task(
        self,
        task: A2ATask,
        target_protocol: str = "i2i",
        adapter_name: Optional[str] = None,
    ) -> I2IBottle:
        """
        Route an A2A Task through the appropriate adapter to produce
        an I2I Bottle for *target_protocol*.
        """
        self.validator.validate_task(task)
        adapter = self._resolve_adapter(adapter_name, task, target_protocol)
        return adapter.receive_task(task)

    # ── Agent Card discovery ────────────────────────────────────

    def build_agent_card(
        self,
        capability_data: dict,
        github_org: str = "SuperInstance",
    ) -> AgentCard:
        """Build an AgentCard from CAPABILITY.toml data."""
        return self._transformer.capability_toml_to_agent_card(
            capability_data, github_org=github_org
        )

    # ── Internals ──────────────────────────────────────────────

    def _resolve_adapter(
        self,
        name: Optional[str],
        msg: object,
        target_protocol: str,
    ) -> Adapter:
        if name:
            return self.registry.get(name)

        # Try to find an adapter whose target_protocol matches
        candidates = self.registry.find_by_protocol(target_protocol)
        if candidates:
            return candidates[0]

        # Fallback: return a fresh default Adapter
        return Adapter()
