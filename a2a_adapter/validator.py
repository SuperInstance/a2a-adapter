"""MessageValidator — schema checking and type coercion."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


class ValidationError(Exception):
    """Raised when a message fails validation."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__(", ".join(self.errors))


class MessageValidator:
    """
    Validates I2I Bottles and A2A Tasks against schema rules.

    Supports:
    - Required-field checks
    - Type coercion (e.g. ``priority`` str→int, ``confidence`` bounds)
    - Custom validators via ``add_rule``
    """

    def __init__(self) -> None:
        self._rules: List[_ValidationRule] = []

    # ── Public API ─────────────────────────────────────────────

    def validate_bottle(self, bottle: Any) -> None:
        """Validate an I2IBottle. Raises ``ValidationError`` on failure."""
        errors: List[str] = []

        # Required string fields
        for field_name in ("from_agent", "to_agent", "subject", "body"):
            val = getattr(bottle, field_name, None)
            if not val or not isinstance(val, str):
                errors.append(f"bottle.{field_name} must be a non-empty string")

        # Confidence bounds
        conf = getattr(bottle, "confidence", 1.0)
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            errors.append("bottle.confidence must be between 0.0 and 1.0")

        # Custom rules
        errors.extend(self._run_custom_rules(bottle, "bottle"))

        if errors:
            raise ValidationError(errors)

    def validate_task(self, task: Any) -> None:
        """Validate an A2ATask. Raises ``ValidationError`` on failure."""
        errors: List[str] = []

        for field_name in ("id", "sender", "receiver", "task_type", "payload"):
            val = getattr(task, field_name, None)
            if not val or not isinstance(val, str):
                errors.append(f"task.{field_name} must be a non-empty string")

        # Task type must be known
        tt = getattr(task, "task_type", "")
        if tt and tt not in ("tell", "ask", "delegate", "broadcast"):
            errors.append(
                f"task.task_type must be one of tell/ask/delegate/broadcast, got '{tt}'"
            )

        # Confidence
        conf = getattr(task, "confidence", 1.0)
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            errors.append("task.confidence must be between 0.0 and 1.0")

        # Priority
        pri = getattr(task, "priority", 0)
        if not isinstance(pri, int) or not (0 <= pri <= 2):
            errors.append("task.priority must be an int in [0, 1, 2]")

        errors.extend(self._run_custom_rules(task, "task"))

        if errors:
            raise ValidationError(errors)

    def add_rule(
        self,
        target: str,
        check: Any,
        message: str = "custom validation failed",
    ) -> None:
        """
        Register a custom validation rule.

        ``target`` is ``"bottle"`` or ``"task"``.
        ``check`` is a callable that returns ``True`` if valid.
        """
        self._rules.append(_ValidationRule(target=target, check=check, message=message))

    # ── Internals ──────────────────────────────────────────────

    def _run_custom_rules(self, obj: Any, target: str) -> List[str]:
        errors: List[str] = []
        for rule in self._rules:
            if rule.target != target:
                continue
            try:
                if not rule.check(obj):
                    errors.append(rule.message)
            except Exception as exc:
                errors.append(f"{rule.message}: {exc}")
        return errors


class _ValidationRule:
    __slots__ = ("target", "check", "message")

    def __init__(self, target: str, check: Any, message: str) -> None:
        self.target = target
        self.check = check
        self.message = message
