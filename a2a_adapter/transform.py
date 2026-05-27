"""MessageTransformer — converting between A2A and I2I message formats."""

from __future__ import annotations

import hashlib
from typing import Dict

from .models import A2ATask, I2IBottle, AgentCard


# Priority mappings
_I2I_TO_A2A_PRIORITY: Dict[str, int] = {
    "🔴": 2,
    "🟡": 1,
    "🟢": 0,
    "🔵": 0,
    "critical": 2,
    "high": 2,
    "normal": 0,
    "low": 0,
}

_A2A_TO_I2I_PRIORITY: Dict[int, str] = {0: "🟢", 1: "🟡", 2: "🔴"}

# Task type inference from subject keywords
_TASK_TYPE_KEYWORDS = {
    "ask": "ask",
    "question": "ask",
    "delegate": "delegate",
    "assign": "delegate",
    "broadcast": "broadcast",
    "announce": "broadcast",
}


class MessageTransformer:
    """Stateless transformer between I2I Bottle and A2A Task formats."""

    # ── Bottle ↔ Task ──────────────────────────────────────────

    def a2a_task_to_bottle(self, task: A2ATask) -> I2IBottle:
        """Convert an A2A Task to an I2I Bottle for edge delivery."""
        return I2IBottle(
            from_agent=task.sender,
            to_agent=task.receiver,
            subject=f"A2A/{task.task_type.upper()}: {task.id}",
            body=task.payload,
            priority=_A2A_TO_I2I_PRIORITY.get(task.priority, "🟢"),
            confidence=task.confidence,
        )

    def bottle_to_a2a_task(self, bottle: I2IBottle) -> A2ATask:
        """Convert an I2I Bottle to an A2A Task for cloud delivery."""
        task_type = self._infer_task_type(bottle.subject)
        priority = _I2I_TO_A2A_PRIORITY.get(bottle.priority, 0)

        task_id = f"i2i-{hashlib.sha256(bottle.subject.encode()).hexdigest()[:8]}"

        return A2ATask(
            id=task_id,
            sender=bottle.from_agent,
            receiver=bottle.to_agent,
            task_type=task_type,
            payload=bottle.body,
            confidence=bottle.confidence,
            priority=priority,
        )

    # ── CAPABILITY.toml → AgentCard ────────────────────────────

    def capability_toml_to_agent_card(
        self,
        cap_data: dict,
        github_org: str = "SuperInstance",
    ) -> AgentCard:
        """Convert CAPABILITY.toml data to an A2A Agent Card."""
        agent = cap_data.get("agent", {})
        caps = cap_data.get("capabilities", {})
        comm = cap_data.get("communication", {})

        skills = []
        for cap_name, cap_detail in caps.items():
            skills.append(
                {
                    "id": cap_name,
                    "name": cap_name.replace("_", " ").title(),
                    "description": cap_detail.get("description", ""),
                    "confidence": cap_detail.get("confidence", 0),
                    "lastUsed": cap_detail.get("last_used", ""),
                }
            )

        auth = {
            "schemes": ["bearer"],
            "credentials": f"github:{github_org}",
        }

        a2a_caps = {
            "streaming": bool(comm.get("mud", False)),
            "pushNotifications": bool(comm.get("issues", False)),
            "stateTransitionHistory": True,
        }

        return AgentCard(
            name=agent.get("name", "unknown"),
            description=f"{agent.get('avatar', '?')} {agent.get('type', 'agent')} — {agent.get('role', '')}",
            url=f"https://github.com/{agent.get('home_repo', f'{github_org}/unknown')}",
            version="1.0.0",
            capabilities=a2a_caps,
            authentication=auth,
            skills=skills,
        )

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _infer_task_type(subject: str) -> str:
        """Infer task type from subject line keywords."""
        lower = subject.lower()
        # Check multi-character keywords first to avoid partial matches
        for keyword, task_type in sorted(
            _TASK_TYPE_KEYWORDS.items(), key=lambda kv: -len(kv[0])
        ):
            if keyword in lower:
                return task_type
        return "tell"


# Module-level convenience functions (backward compat)
_capability_toml_to_agent_card = MessageTransformer().capability_toml_to_agent_card


def capability_toml_to_agent_card(
    cap_data: dict, github_org: str = "SuperInstance"
) -> AgentCard:
    """Module-level convenience: convert CAPABILITY.toml → AgentCard."""
    return _capability_toml_to_agent_card(cap_data, github_org)
