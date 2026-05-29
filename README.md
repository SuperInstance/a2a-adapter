# a2a-adapter

**I2I ↔ Google A2A protocol bridge** — git-native agents join the Google A2A ecosystem. Translates between FLUX I2I (offline-first, bottle-based) and Google A2A (HTTP/JSON-RPC, Agent Cards).

## What This Gives You

- **Bidirectional translation** — I2I bottles ↔ A2A tasks
- **Protocol bridge** — route messages between FLUX and A2A ecosystems
- **Agent registry** — register I2I agents as A2A Agent Cards
- **Message validation** — schema validation for both protocols

## Installation

```bash
pip install a2a-adapter
```

## Quick Start

```python
from a2a_adapter import I2IBottle, ProtocolBridge

bridge = ProtocolBridge()

# I2I → A2A
bottle = I2IBottle(
    from_agent="edge-agent",
    to_agent="cloud-agent",
    subject="ask: status check",
    body="What is the current system load?",
)
task = bridge.route_bottle(bottle, target_protocol="a2a")

# A2A → I2I
bottle = bridge.route_task(task, target_protocol="i2i")
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## How It Fits

Bridges the offline-first `a2a-protocol` fleet with the Google A2A standard. Enables SuperInstance agents to participate in both ecosystems simultaneously.

## License

MIT
