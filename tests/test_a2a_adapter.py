"""Comprehensive test suite for a2a_adapter."""

import pytest

from a2a_adapter import (
    AgentCard,
    A2ATask,
    I2IBottle,
    Adapter,
    ProtocolBridge,
    MessageTransformer,
    MessageValidator,
    ValidationError,
    AdapterRegistry,
    capability_toml_to_agent_card,
)
from a2a_adapter.models import I2IBottle as Bottle


# ── Models ────────────────────────────────────────────────────


class TestAgentCard:
    def test_to_a2a_json(self):
        card = AgentCard(name="X", description="d", url="https://x.io")
        j = card.to_a2a_json()
        assert j["schemaVersion"] == "1.0"
        assert j["name"] == "X"
        assert j["url"] == "https://x.io"
        assert "capabilities" in j

    def test_from_a2a_json_roundtrip(self):
        card = AgentCard(
            name="Bot",
            description="Test bot",
            url="https://bot.io",
            version="2.0.0",
            capabilities={"streaming": True},
            skills=[{"id": "s1"}],
        )
        j = card.to_a2a_json()
        card2 = AgentCard.from_a2a_json(j)
        assert card2.name == "Bot"
        assert card2.version == "2.0.0"
        assert card2.capabilities["streaming"] is True
        assert len(card2.skills) == 1

    def test_default_fields(self):
        card = AgentCard(name="A", description="B", url="C")
        assert card.version == "1.0.0"
        assert card.capabilities == {}
        assert card.skills == []


class TestA2ATask:
    def test_to_a2a_message(self):
        task = A2ATask(
            id="t1", sender="S", receiver="R",
            task_type="ask", payload="hi",
        )
        msg = task.to_a2a_message()
        assert msg["jsonrpc"] == "2.0"
        assert msg["id"] == "t1"
        assert "task" in msg["params"]

    def test_from_a2a_message(self):
        task = A2ATask(
            id="t2", sender="A", receiver="B",
            task_type="tell", payload="yo", priority=1,
        )
        msg = task.to_a2a_message()
        task2 = A2ATask.from_a2a_message(msg)
        assert task2.id == "t2"
        assert task2.sender == "A"
        assert task2.task_type == "tell"
        assert task2.priority == 1


class TestI2IBottle:
    def test_to_markdown(self):
        b = I2IBottle(
            from_agent="X", to_agent="Y",
            subject="Hello", body="World", priority="🟢",
        )
        md = b.to_markdown()
        assert "# Hello" in md
        assert "**From:** X" in md
        assert "World" in md

    def test_from_markdown(self):
        md = (
            "# Test Subject\n\n"
            "**From:** Alice\n**To:** Bob\n"
            "**Date:** 2026-01-01\n**Priority:** 🔴\n"
            "**Confidence:** 85%\n\n"
            "Body text here.\n"
        )
        b = I2IBottle.from_markdown(md)
        assert b.from_agent == "Alice"
        assert b.to_agent == "Bob"
        assert b.subject == "Test Subject"
        assert b.body == "Body text here."
        assert abs(b.confidence - 0.85) < 0.01

    def test_compute_hash_deterministic(self):
        b1 = I2IBottle(
            from_agent="A", to_agent="B",
            subject="S", body="body",
        )
        b2 = I2IBottle(
            from_agent="A", to_agent="B",
            subject="S", body="body",
        )
        assert b1.compute_hash() == b2.compute_hash()

    def test_compute_hash_differs(self):
        b1 = I2IBottle(from_agent="A", to_agent="B", subject="S1", body="x")
        b2 = I2IBottle(from_agent="A", to_agent="B", subject="S2", body="x")
        assert b1.compute_hash() != b2.compute_hash()


# ── Transformer ───────────────────────────────────────────────


class TestMessageTransformer:
    def setup_method(self):
        self.t = MessageTransformer()

    def test_bottle_to_task_basic(self):
        bottle = I2IBottle(
            from_agent="A", to_agent="B",
            subject="hello", body="world",
        )
        task = self.t.bottle_to_a2a_task(bottle)
        assert task.sender == "A"
        assert task.receiver == "B"
        assert task.payload == "world"
        assert task.task_type == "tell"

    def test_bottle_to_task_ask_keyword(self):
        bottle = I2IBottle(
            from_agent="A", to_agent="B",
            subject="please ask about X", body="",
        )
        task = self.t.bottle_to_a2a_task(bottle)
        assert task.task_type == "ask"

    def test_bottle_to_task_delegate_keyword(self):
        bottle = I2IBottle(
            from_agent="A", to_agent="B",
            subject="delegate this task", body="",
        )
        task = self.t.bottle_to_a2a_task(bottle)
        assert task.task_type == "delegate"

    def test_bottle_to_task_broadcast_keyword(self):
        bottle = I2IBottle(
            from_agent="A", to_agent="B",
            subject="broadcast announcement", body="",
        )
        task = self.t.bottle_to_a2a_task(bottle)
        assert task.task_type == "broadcast"

    def test_task_to_bottle_priority(self):
        task = A2ATask(
            id="x", sender="A", receiver="B",
            task_type="tell", payload="p", priority=2,
        )
        bottle = self.t.a2a_task_to_bottle(task)
        assert bottle.priority == "🔴"
        assert bottle.from_agent == "A"

    def test_roundtrip(self):
        orig = I2IBottle(
            from_agent="A", to_agent="B",
            subject="test", body="hello", priority="🟢", confidence=0.9,
        )
        task = self.t.bottle_to_a2a_task(orig)
        back = self.t.a2a_task_to_bottle(task)
        assert back.from_agent == orig.from_agent
        assert back.to_agent == orig.to_agent
        assert back.body == orig.body

    def test_capability_toml_to_agent_card(self):
        cap = {
            "agent": {
                "name": "TestAgent",
                "type": "vessel",
                "avatar": "⚡",
                "home_repo": "Org/test-vessel",
            },
            "capabilities": {
                "testing": {
                    "confidence": 0.9,
                    "last_used": "2026-04-12",
                    "description": "Test specialist",
                }
            },
            "communication": {"mud": True, "issues": True},
        }
        card = self.t.capability_toml_to_agent_card(cap)
        j = card.to_a2a_json()
        assert j["name"] == "TestAgent"
        assert j["capabilities"]["streaming"] is True
        assert len(j["skills"]) == 1


# ── Validator ─────────────────────────────────────────────────


class TestMessageValidator:
    def setup_method(self):
        self.v = MessageValidator()

    def test_valid_bottle(self):
        b = I2IBottle(from_agent="A", to_agent="B", subject="S", body="X")
        self.v.validate_bottle(b)  # should not raise

    def test_invalid_bottle_empty_fields(self):
        b = I2IBottle(from_agent="", to_agent="B", subject="S", body="X")
        with pytest.raises(ValidationError) as exc_info:
            self.v.validate_bottle(b)
        assert "from_agent" in str(exc_info.value)

    def test_invalid_bottle_confidence(self):
        b = I2IBottle(
            from_agent="A", to_agent="B", subject="S", body="X",
            confidence=5.0,
        )
        with pytest.raises(ValidationError):
            self.v.validate_bottle(b)

    def test_valid_task(self):
        t = A2ATask(
            id="1", sender="A", receiver="B",
            task_type="tell", payload="p",
        )
        self.v.validate_task(t)

    def test_invalid_task_type(self):
        t = A2ATask(
            id="1", sender="A", receiver="B",
            task_type="invalid", payload="p",
        )
        with pytest.raises(ValidationError) as exc_info:
            self.v.validate_task(t)
        assert "task_type" in str(exc_info.value)

    def test_invalid_task_priority(self):
        t = A2ATask(
            id="1", sender="A", receiver="B",
            task_type="tell", payload="p", priority=99,
        )
        with pytest.raises(ValidationError):
            self.v.validate_task(t)

    def test_custom_rule(self):
        self.v.add_rule(
            "bottle",
            lambda b: b.from_agent != "evil",
            "evil agents not allowed",
        )
        good = I2IBottle(from_agent="good", to_agent="B", subject="S", body="X")
        self.v.validate_bottle(good)

        bad = I2IBottle(from_agent="evil", to_agent="B", subject="S", body="X")
        with pytest.raises(ValidationError) as exc_info:
            self.v.validate_bottle(bad)
        assert "evil" in str(exc_info.value)


# ── Adapter ───────────────────────────────────────────────────


class TestAdapter:
    def test_send_bottle(self):
        adapter = Adapter()
        bottle = I2IBottle(
            from_agent="A", to_agent="B",
            subject="test", body="hello",
        )
        task = adapter.send_bottle(bottle)
        assert task.sender == "A"
        assert task.payload == "hello"

    def test_receive_task(self):
        adapter = Adapter()
        task = A2ATask(
            id="t1", sender="A", receiver="B",
            task_type="ask", payload="what?",
        )
        bottle = adapter.receive_task(task)
        assert bottle.from_agent == "A"
        assert bottle.body == "what?"

    def test_send_invalid_bottle_raises(self):
        adapter = Adapter()
        bottle = I2IBottle(from_agent="", to_agent="", subject="", body="")
        with pytest.raises(ValidationError):
            adapter.send_bottle(bottle)

    def test_info(self):
        a = Adapter()
        info = a.info()
        assert "name" in info


# ── Registry ──────────────────────────────────────────────────


class TestAdapterRegistry:
    def test_register_and_get(self):
        reg = AdapterRegistry()
        a = Adapter()
        reg.register(a)
        assert reg.get("base") is a

    def test_get_missing_raises(self):
        reg = AdapterRegistry()
        with pytest.raises(KeyError):
            reg.get("nope")

    def test_unregister(self):
        reg = AdapterRegistry()
        reg.register(Adapter())
        reg.unregister("base")
        assert "base" not in reg

    def test_unregister_missing_raises(self):
        reg = AdapterRegistry()
        with pytest.raises(KeyError):
            reg.unregister("nope")

    def test_find_by_protocol(self):
        class A2AAdapter(Adapter):
            name = "i2i_a2a"
            target_protocol = "a2a"

        reg = AdapterRegistry()
        reg.register(A2AAdapter())
        results = reg.find_by_protocol("a2a")
        assert len(results) == 1
        assert results[0].name == "i2i_a2a"

    def test_find_by_source(self):
        class SrcAdapter(Adapter):
            name = "src_i2i"
            source_protocol = "i2i"

        reg = AdapterRegistry()
        reg.register(SrcAdapter())
        results = reg.find_by_source("i2i")
        assert len(results) == 1

    def test_list_names(self):
        reg = AdapterRegistry()
        a1 = Adapter()
        a1.name = "one"
        a2 = Adapter()
        a2.name = "two"
        reg.register(a1)
        reg.register(a2)
        assert set(reg.list_names()) == {"one", "two"}

    def test_len_and_contains(self):
        reg = AdapterRegistry()
        assert len(reg) == 0
        reg.register(Adapter())
        assert len(reg) == 1
        assert "base" in reg


# ── ProtocolBridge ────────────────────────────────────────────


class TestProtocolBridge:
    def test_route_bottle(self):
        bridge = ProtocolBridge()
        bottle = I2IBottle(
            from_agent="A", to_agent="B",
            subject="test", body="msg",
        )
        task = bridge.route_bottle(bottle)
        assert task.sender == "A"

    def test_route_task(self):
        bridge = ProtocolBridge()
        task = A2ATask(
            id="t1", sender="A", receiver="B",
            task_type="tell", payload="hi",
        )
        bottle = bridge.route_task(task)
        assert bottle.from_agent == "A"

    def test_register_and_use_adapter(self):
        class MyAdapter(Adapter):
            name = "custom"
            target_protocol = "a2a"

        bridge = ProtocolBridge()
        bridge.register_adapter(MyAdapter())
        assert "custom" in bridge.list_adapters()

        bottle = I2IBottle(
            from_agent="A", to_agent="B",
            subject="s", body="b",
        )
        task = bridge.route_bottle(bottle, adapter_name="custom")
        assert task.sender == "A"

    def test_build_agent_card(self):
        bridge = ProtocolBridge()
        cap = {
            "agent": {"name": "X", "type": "t", "avatar": "🔧"},
            "capabilities": {},
            "communication": {},
        }
        card = bridge.build_agent_card(cap)
        assert card.name == "X"

    def test_route_invalid_bottle_raises(self):
        bridge = ProtocolBridge()
        bottle = I2IBottle(from_agent="", to_agent="", subject="", body="")
        with pytest.raises(ValidationError):
            bridge.route_bottle(bottle)


# ── Module-level convenience ──────────────────────────────────


class TestModuleConvenience:
    def test_capability_toml_convenience(self):
        cap = {
            "agent": {"name": "M", "type": "v"},
            "capabilities": {},
            "communication": {},
        }
        card = capability_toml_to_agent_card(cap)
        assert card.name == "M"
