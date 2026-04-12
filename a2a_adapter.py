#!/usr/bin/env python3
"""
A2A Adapter — translates between FLUX I2I protocol and Google A2A standard.

I2I: git-native, offline-first, bottle-based
A2A: HTTP/JSON-RPC, online-only, Agent Cards

This adapter bridges the two worlds:
- Exposes fleet agents as A2A-compatible Agent Cards
- Translates I2I bottles to A2A Tasks
- Translates A2A messages to I2I bottles for edge agents

Reference: https://a2aprotocol.ai/
"""

import json
import hashlib
import time
from typing import Optional
from dataclasses import dataclass, field

try:
    import tomllib
except ImportError:
    import tomli as tomllib


@dataclass
class AgentCard:
    """A2A Agent Card — JSON capability advertisement."""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    capabilities: dict = field(default_factory=dict)
    authentication: dict = field(default_factory=dict)
    skills: list = field(default_factory=list)

    def to_a2a_json(self) -> dict:
        """Convert to A2A Agent Card format."""
        return {
            "schemaVersion": "1.0",
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities,
            "authentication": self.authentication,
            "skills": self.skills,
        }


@dataclass
class A2ATask:
    """A2A Task — a unit of work exchanged between agents."""
    id: str
    sender: str
    receiver: str
    task_type: str  # "tell", "ask", "delegate", "broadcast"
    payload: str
    confidence: float = 1.0
    deadline_ms: Optional[int] = None
    priority: int = 0

    def to_a2a_message(self) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": f"agents/{self.receiver}/tasks",
            "params": {
                "task": {
                    "id": self.id,
                    "type": self.task_type,
                    "payload": self.payload,
                    "metadata": {
                        "confidence": self.confidence,
                        "priority": self.priority,
                        "sender": self.sender,
                        "deadline_ms": self.deadline_ms,
                    }
                }
            },
            "id": self.id
        }


@dataclass
class I2IBottle:
    """I2I Bottle — git-native message."""
    from_agent: str
    to_agent: str
    subject: str
    body: str
    priority: str = "normal"  # 🔴🟡🟢🔵
    timestamp: str = ""
    confidence: float = 1.0

    def to_markdown(self) -> str:
        return f"""# {self.subject}

**From:** {self.from_agent}
**To:** {self.to_agent}
**Date:** {self.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
**Priority:** {self.priority}
**Confidence:** {self.confidence:.0%}

{self.body}
"""


def capability_toml_to_agent_card(cap_data: dict, github_org: str = "SuperInstance") -> AgentCard:
    """Convert CAPABILITY.toml to A2A Agent Card."""
    agent = cap_data.get("agent", {})
    caps = cap_data.get("capabilities", {})
    comm = cap_data.get("communication", {})
    resources = cap_data.get("resources", {})

    # Build skills list from capabilities
    skills = []
    for cap_name, cap_data_item in caps.items():
        skills.append({
            "id": cap_name,
            "name": cap_name.replace("_", " ").title(),
            "description": cap_data_item.get("description", ""),
            "confidence": cap_data_item.get("confidence", 0),
            "lastUsed": cap_data_item.get("last_used", ""),
        })

    # Build authentication from agent type
    auth = {
        "schemes": ["bearer"],
        "credentials": f"github:{github_org}",
    }

    # Build capabilities
    a2a_caps = {
        "streaming": comm.get("mud", False),
        "pushNotifications": comm.get("issues", False),
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


def a2a_task_to_bottle(task: A2ATask) -> I2IBottle:
    """Convert A2A Task to I2I Bottle for edge delivery."""
    priority_map = {0: "🟢", 1: "🟡", 2: "🔴"}
    return I2IBottle(
        from_agent=task.sender,
        to_agent=task.receiver,
        subject=f"A2A/{task.task_type.upper()}: {task.id}",
        body=task.payload,
        priority=priority_map.get(task.priority, "🟢"),
        confidence=task.confidence,
    )


def bottle_to_a2a_task(bottle: I2IBottle) -> A2ATask:
    """Convert I2I Bottle to A2A Task for cloud delivery."""
    task_type = "tell"
    subject = bottle.subject.lower()
    if "ask" in subject: task_type = "ask"
    elif "delegate" in subject: task_type = "delegate"
    elif "broadcast" in subject: task_type = "broadcast"

    priority_map = {"🔴": 2, "🟡": 1, "🟢": 0, "🔵": 0}

    return A2ATask(
        id=f"i2i-{hashlib.sha256(bottle.subject.encode()).hexdigest()[:8]}",
        sender=bottle.from_agent,
        receiver=bottle.to_agent,
        task_type=task_type,
        payload=bottle.body,
        confidence=bottle.confidence,
        priority=priority_map.get(bottle.priority, 0),
    )


# ── Tests ──────────────────────────────────────────────────────

def test_capability_to_agent_card():
    cap = {
        "agent": {"name": "TestAgent", "type": "vessel", "avatar": "⚡",
                  "home_repo": "Org/test-vessel"},
        "capabilities": {
            "testing": {"confidence": 0.9, "last_used": "2026-04-12",
                       "description": "Test specialist"}
        },
        "communication": {"mud": True, "issues": True}
    }
    card = capability_toml_to_agent_card(cap)
    j = card.to_a2a_json()
    assert j["name"] == "TestAgent"
    assert j["capabilities"]["streaming"] == True
    assert len(j["skills"]) == 1
    assert j["skills"][0]["id"] == "testing"
    print("✅ test_capability_to_agent_card")


def test_a2a_task_to_bottle():
    task = A2ATask(
        id="t1", sender="Oracle1", receiver="JetsonClaw1",
        task_type="tell", payload="ISA v3 draft ready", priority=2
    )
    bottle = a2a_task_to_bottle(task)
    assert bottle.from_agent == "Oracle1"
    assert bottle.priority == "🔴"
    assert "ISA v3" in bottle.body
    print("✅ test_a2a_task_to_bottle")


def test_bottle_to_a2a_task():
    bottle = I2IBottle(
        from_agent="JetsonClaw1", to_agent="Oracle1",
        subject="A2A/ASK: edge encoding review",
        body="Reviewed the prefix byte scheme. Looks good.",
        priority="🟡", confidence=0.85
    )
    task = bottle_to_a2a_task(bottle)
    assert task.sender == "JetsonClaw1"
    assert task.task_type == "ask"
    assert task.priority == 1
    assert task.confidence == 0.85
    print("✅ test_bottle_to_a2a_task")


def test_roundtrip():
    """Bottle → A2A Task → Bottle preserves semantics."""
    orig = I2IBottle(
        from_agent="A", to_agent="B",
        subject="test",
        body="hello", priority="🟢", confidence=0.9
    )
    task = bottle_to_a2a_task(orig)
    back = a2a_task_to_bottle(task)
    assert back.from_agent == orig.from_agent
    assert back.to_agent == orig.to_agent
    assert back.body == orig.body
    print("✅ test_roundtrip")


def test_agent_card_json_schema():
    """Verify Agent Card matches A2A spec structure."""
    card = AgentCard(
        name="Test", description="Test agent", url="https://example.com"
    )
    j = card.to_a2a_json()
    assert "schemaVersion" in j
    assert "name" in j
    assert "url" in j
    assert "capabilities" in j
    assert "skills" in j
    print("✅ test_agent_card_json_schema")


if __name__ == "__main__":
    test_capability_to_agent_card()
    test_a2a_task_to_bottle()
    test_bottle_to_a2a_task()
    test_roundtrip()
    test_agent_card_json_schema()
    print("\n5/5 A2A adapter tests passing ✅")
