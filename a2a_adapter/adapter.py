"""Base Adapter class with transform/validate pipeline."""

from __future__ import annotations

from typing import Any, Optional, Type
from .models import A2ATask, I2IBottle
from .validator import MessageValidator, ValidationError
from .transform import MessageTransformer


class Adapter:
    """
    Base adapter implementing a transform → validate → deliver pipeline.

    Subclass and override ``transform_in``, ``transform_out``, or
    ``deliver`` to create protocol-specific adapters.
    """

    name: str = "base"
    source_protocol: str = "unknown"
    target_protocol: str = "unknown"

    def __init__(
        self,
        transformer: Optional[MessageTransformer] = None,
        validator: Optional[MessageValidator] = None,
    ) -> None:
        self.transformer = transformer or MessageTransformer()
        self.validator = validator or MessageValidator()
        self._last_error: Optional[ValidationError] = None

    # ── Pipeline entry points ──────────────────────────────────

    def send_bottle(self, bottle: I2IBottle) -> A2ATask:
        """Convert an I2I Bottle to an A2A Task (outbound)."""
        self._last_error = None
        self.validator.validate_bottle(bottle)
        task = self.transform_in(bottle)
        self.validator.validate_task(task)
        return task

    def receive_task(self, task: A2ATask) -> I2IBottle:
        """Convert an A2A Task to an I2I Bottle (inbound)."""
        self._last_error = None
        self.validator.validate_task(task)
        bottle = self.transform_out(task)
        self.validator.validate_bottle(bottle)
        return bottle

    # ── Transform hooks ────────────────────────────────────────

    def transform_in(self, bottle: I2IBottle) -> A2ATask:
        """Bottle → Task. Override for custom logic."""
        return self.transformer.bottle_to_a2a_task(bottle)

    def transform_out(self, task: A2ATask) -> I2IBottle:
        """Task → Bottle. Override for custom logic."""
        return self.transformer.a2a_task_to_bottle(task)

    # ── Metadata ───────────────────────────────────────────────

    @property
    def last_error(self) -> Optional[ValidationError]:
        return self._last_error

    def info(self) -> dict:
        return {
            "name": self.name,
            "source_protocol": self.source_protocol,
            "target_protocol": self.target_protocol,
        }
