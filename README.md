# A2A Adapter

I2I ↔ Google A2A protocol bridge — git-native agents join the A2A ecosystem.

## Meta

**Domain:** agent-coordination  
**Implements:** a2a-protocol, i2i-bridge, agent-interop  
**License:** MIT

## Overview

A2A Adapter translates between the FLUX I2I protocol (git-native, offline-first, bottle-based) and the Google A2A standard (HTTP/JSON-RPC, online-only, Agent Cards).

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from a2a_adapter import I2IBottle, ProtocolBridge

bridge = ProtocolBridge()

# Send an I2I bottle → get an A2A task
bottle = I2IBottle(
    from_agent="edge-agent",
    to_agent="cloud-agent",
    subject="ask: status check",
    body="What is the current system load?",
    priority="🟡",
    confidence=0.9,
)
task = bridge.route_bottle(bottle, target_protocol="a2a")
print(task.to_a2a_message())

# Receive an A2A task → get an I2I bottle
from a2a_adapter import A2ATask
task = A2ATask(
    id="t1", sender="cloud", receiver="edge",
    task_type="tell", payload="Load is 42%", priority=0,
)
bottle = bridge.route_task(task, target_protocol="i2i")
print(bottle.to_markdown())
```

## Architecture

```
a2a_adapter/
├── __init__.py       # Public API exports
├── models.py         # AgentCard, A2ATask, I2IBottle dataclasses
├── adapter.py        # Base Adapter with transform/validate pipeline
├── bridge.py         # ProtocolBridge orchestrating message routing
├── transform.py      # MessageTransformer (format conversion)
├── validator.py      # MessageValidator with schema checking
└── registry.py       # AdapterRegistry for adapter discovery
```

## Core Components

### Adapter

Base class implementing a **transform → validate → deliver** pipeline. Subclass to create protocol-specific adapters:

```python
from a2a_adapter import Adapter

class MyAdapter(Adapter):
    name = "custom"
    source_protocol = "i2i"
    target_protocol = "a2a"

    def transform_in(self, bottle):
        # Custom bottle → task logic
        return super().transform_in(bottle)
```

### ProtocolBridge

Orchestrates message translation between protocols:

```python
from a2a_adapter import ProtocolBridge

bridge = ProtocolBridge()
bridge.register_adapter(MyAdapter())

task = bridge.route_bottle(bottle, target_protocol="a2a")
```

### MessageValidator

Validates messages with built-in rules and custom checks:

```python
from a2a_adapter import MessageValidator

v = MessageValidator()
v.add_rule("bottle", lambda b: b.from_agent != "blocked", "Agent blocked")
v.validate_bottle(bottle)  # Raises ValidationError on failure
```

### AdapterRegistry

Discovers and loads adapters by protocol:

```python
from a2a_adapter import AdapterRegistry

reg = AdapterRegistry()
reg.register(my_adapter)
reg.find_by_protocol("a2a")  # All adapters targeting A2A
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Protocol Reference

- **I2I Bottle**: Git-native message with `from_agent`, `to_agent`, `subject`, `body`, `priority` (🔴🟡🟢🔵), `confidence`
- **A2A Task**: JSON-RPC message with `id`, `sender`, `receiver`, `task_type` (tell/ask/delegate/broadcast), `payload`, `priority` (0-2)
- **Agent Card**: JSON capability advertisement per the A2A spec
