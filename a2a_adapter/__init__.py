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

from .models import AgentCard, A2ATask, I2IBottle
from .adapter import Adapter
from .bridge import ProtocolBridge
from .transform import MessageTransformer, capability_toml_to_agent_card
from .validator import MessageValidator, ValidationError
from .registry import AdapterRegistry

__all__ = [
    "AgentCard",
    "A2ATask",
    "I2IBottle",
    "Adapter",
    "ProtocolBridge",
    "MessageTransformer",
    "MessageValidator",
    "ValidationError",
    "AdapterRegistry",
    "capability_toml_to_agent_card",
]

__version__ = "0.1.0"
