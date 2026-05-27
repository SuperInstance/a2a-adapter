"""Core data models for A2A and I2I protocols."""

import hashlib
import time
from typing import Optional
from dataclasses import dataclass, field


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

    @classmethod
    def from_a2a_json(cls, data: dict) -> "AgentCard":
        """Construct from A2A Agent Card JSON dict."""
        return cls(
            name=data["name"],
            description=data["description"],
            url=data["url"],
            version=data.get("version", "1.0.0"),
            capabilities=data.get("capabilities", {}),
            authentication=data.get("authentication", {}),
            skills=data.get("skills", []),
        )


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
        """Convert to A2A JSON-RPC message envelope."""
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
                    },
                }
            },
            "id": self.id,
        }

    @classmethod
    def from_a2a_message(cls, msg: dict) -> "A2ATask":
        """Construct from an A2A JSON-RPC message envelope."""
        params = msg["params"]
        task = params["task"]
        meta = task.get("metadata", {})
        return cls(
            id=task["id"],
            sender=meta.get("sender", ""),
            receiver=msg["method"].split("/")[1] if "/" in msg.get("method", "") else "",
            task_type=task["type"],
            payload=task["payload"],
            confidence=meta.get("confidence", 1.0),
            deadline_ms=meta.get("deadline_ms"),
            priority=meta.get("priority", 0),
        )


@dataclass
class I2IBottle:
    """I2I Bottle — git-native message container."""

    from_agent: str
    to_agent: str
    subject: str
    body: str
    priority: str = "normal"  # 🔴🟡🟢🔵 or textual
    timestamp: str = ""
    confidence: float = 1.0

    def to_markdown(self) -> str:
        """Render bottle as markdown document."""
        ts = self.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return (
            f"# {self.subject}\n\n"
            f"**From:** {self.from_agent}\n"
            f"**To:** {self.to_agent}\n"
            f"**Date:** {ts}\n"
            f"**Priority:** {self.priority}\n"
            f"**Confidence:** {self.confidence:.0%}\n\n"
            f"{self.body}\n"
        )

    @classmethod
    def from_markdown(cls, md: str) -> "I2IBottle":
        """Parse a markdown bottle back into an I2IBottle."""
        lines = md.strip().split("\n")
        subject = lines[0].lstrip("# ").strip() if lines else ""
        meta: dict = {}
        for line in lines[1:]:
            if line.startswith("**") and ":**" in line:
                key, _, value = line.strip("*").partition(":**")
                meta[key.strip().lower()] = value.strip()

        # Body is everything after the metadata block
        body_start = 0
        for i, line in enumerate(lines):
            if line.strip() == "" and i > 0 and any(
                l.startswith("**") for l in lines[max(0, i - 4) : i]
            ):
                body_start = i + 1
                break

        body = "\n".join(lines[body_start:]).strip() if body_start else ""

        conf_str = meta.get("confidence", "100%").rstrip("%")
        try:
            confidence = float(conf_str) / 100.0
        except ValueError:
            confidence = 1.0

        return cls(
            from_agent=meta.get("from", ""),
            to_agent=meta.get("to", ""),
            subject=subject,
            body=body,
            priority=meta.get("priority", "normal"),
            timestamp=meta.get("date", ""),
            confidence=confidence,
        )

    def compute_hash(self) -> str:
        """Deterministic hash of the bottle contents."""
        raw = f"{self.from_agent}:{self.to_agent}:{self.subject}:{self.body}"
        return hashlib.sha256(raw.encode()).hexdigest()
