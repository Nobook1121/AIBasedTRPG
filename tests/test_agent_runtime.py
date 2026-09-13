from trpg_server.agents.context import AgentRequestContext
from trpg_server.agents.profiles import AgentProfile
from trpg_server.agents.runtime import run_agent_completion
from trpg_server.agents.tools.base import AgentTool, ToolRegistry
from trpg_server.json_store import read_json


class FakeRequester:
    def __init__(self):
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)
        if len(self.calls) == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {"name": "test.echo", "arguments": "{\"value\":\"hello\"}"},
                                }
                            ],
                        }
                    }
                ]
            }
        return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}], "usage": {"total_tokens": 9}}


class FakeCheckRequester:
    def __init__(self):
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)
        if len(self.calls) == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call-check",
                                    "type": "function",
                                    "function": {"name": "check.roll_room_check", "arguments": "{}"},
                                }
                            ],
                        }
                    }
                ]
            }
        return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}], "usage": {"total_tokens": 9}}


def test_runtime_executes_enabled_tool_and_finishes():
    tool = AgentTool(
        name="test.echo",
        description="Echo value",
        parameters={"type": "object", "properties": {"value": {"type": "string"}}},
        handler=lambda arguments, context: {"echo": arguments["value"], "room_id": context.room_id},
    )
    requester = FakeRequester()

    result = run_agent_completion(
        requester=requester,
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "@KP hi"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["test.echo"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert result.content == "final answer"
    assert result.token_count == 9
    assert len(requester.calls) == 2
    assert requester.calls[0]["tools"][0]["function"]["name"] == "test.echo"
    assert requester.calls[1]["messages"][-1]["role"] == "tool"


def test_runtime_accumulates_token_count_across_multiple_tool_rounds():
    class MultiRoundRequester:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "test.echo", "arguments": "{}"},
                            }],
                        }
                    }],
                    "usage": {"total_tokens": 11},
                }
            if len(self.calls) == 2:
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": "call-2",
                                "type": "function",
                                "function": {"name": "test.echo", "arguments": "{}"},
                            }],
                        }
                    }],
                    "usage": {"total_tokens": 13},
                }
            return {
                "choices": [{"message": {"role": "assistant", "content": "final answer"}}],
                "usage": {"total_tokens": 17},
            }

    tool = AgentTool(
        name="test.echo",
        description="Echo value",
        parameters={"type": "object", "properties": {}},
        handler=lambda arguments, context: {"ok": True},
    )

    result = run_agent_completion(
        requester=MultiRoundRequester(),
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "@KP hi"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["test.echo"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert result.content == "final answer"
    assert result.token_count == 41


def test_runtime_returns_tool_result_to_model_and_collects_visible_message():
    class VisibleToolRequester:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "test.check", "arguments": "{}"},
                            }],
                        }
                    }]
                }
            return {"choices": [{"message": {"role": "assistant", "content": "continued"}}]}

    tool_result = {
        "roll": 17,
        "summary": "侦查 d%: [17] = 17 / 50 成功",
        "visible_message": {
            "type": "dice",
            "sender_name": "骰娘",
            "content": "侦查 d%: [17] = 17 / 50 成功",
        },
    }
    requester = VisibleToolRequester()
    tool = AgentTool(
        name="test.check",
        description="Check",
        parameters={"type": "object", "properties": {}},
        handler=lambda arguments, context: tool_result,
    )

    result = run_agent_completion(
        requester=requester,
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "check"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["test.check"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert result.content == "continued"
    assert result.tool_messages == [tool_result["visible_message"]]
    assert '"roll": 17' in requester.calls[1]["messages"][-1]["content"]
    assert "侦查 d%: [17] = 17 / 50 成功" in requester.calls[1]["messages"][-1]["content"]


def test_runtime_continues_after_direct_message_tool_and_collects_both_messages():
    class TriggerRequester:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": "call-trigger",
                                "type": "function",
                                "function": {"name": "test.trigger", "arguments": "{\"trigger_id\": 2}"},
                            }],
                        },
                    }],
                }
            return {"choices": [{"message": {"role": "assistant", "content": "KP decision"}}]}

    direct_message = {
        "type": "trigger",
        "sender_name": "note",
        "content": "hidden note",
    }
    visible_message = {
        "type": "dice",
        "sender_name": "dice",
        "content": "check failed",
    }
    requester = TriggerRequester()
    tool = AgentTool(
        name="test.trigger",
        description="Reveal trigger",
        parameters={"type": "object", "properties": {"trigger_id": {"type": "integer"}}},
        handler=lambda arguments, context: {
            "direct_message": direct_message,
            "visible_message": visible_message,
            "trigger_id": arguments["trigger_id"],
        },
    )

    result = run_agent_completion(
        requester=requester,
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "check"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["test.trigger"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert len(requester.calls) == 2
    assert result.content == "KP decision"
    assert result.tool_messages == [visible_message]
    assert result.direct_messages == [direct_message]


def test_runtime_sanitizes_assistant_content_when_tool_calls_are_present():
    class NoisyToolRequester:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "noisy protocol text that must not be replayed",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {"name": "test.echo", "arguments": "{\"value\":\"hello\"}"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}]}

    tool = AgentTool(
        name="test.echo",
        description="Echo value",
        parameters={"type": "object", "properties": {"value": {"type": "string"}}},
        handler=lambda arguments, context: {"echo": arguments["value"]},
    )
    requester = NoisyToolRequester()

    result = run_agent_completion(
        requester=requester,
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "@KP hi"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["test.echo"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    replayed_assistant_message = requester.calls[1]["messages"][-2]
    assert result.content == "final answer"
    assert replayed_assistant_message["role"] == "assistant"
    assert replayed_assistant_message["content"] == ""
    assert "noisy protocol text" not in str(requester.calls[1]["messages"])


def test_runtime_treats_non_object_tool_arguments_as_empty_dict():
    class NumericArgumentRequester:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {"name": "test.echo", "arguments": "10"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}]}

    seen_arguments = []
    tool = AgentTool(
        name="test.echo",
        description="Echo value",
        parameters={"type": "object", "properties": {}},
        handler=lambda arguments, context: seen_arguments.append(arguments) or {"ok": True},
    )

    result = run_agent_completion(
        requester=NumericArgumentRequester(),
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "@KP hi"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["test.echo"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert result.content == "final answer"
    assert seen_arguments == [{}]


def test_runtime_resolves_underscore_tool_name_aliases():
    class AliasRequester:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "room_get_room_snapshot",
                                            "arguments": "{\"include_inactive\":false}",
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}]}

    seen_calls = []
    tool = AgentTool(
        name="room.get_room_snapshot",
        description="Load snapshot",
        parameters={"type": "object", "properties": {}},
        handler=lambda arguments, context: seen_calls.append(arguments) or {"ok": True},
    )

    result = run_agent_completion(
        requester=AliasRequester(),
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "@KP hi"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["room.get_room_snapshot"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert result.content == "final answer"
    assert seen_calls == [{"include_inactive": False}]


def test_runtime_rejects_unauthorized_tool():
    requester = FakeRequester()

    result = run_agent_completion(
        requester=requester,
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "@KP hi"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=[]),
        registry=ToolRegistry([]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert result.error == "Tool test.echo is not enabled for agent kp"


def test_build_agent_context_resolves_room_dir_and_scenarios_dir(tmp_path):
    from trpg_server.agents.context import build_agent_context

    rooms_dir = tmp_path / "rooms"
    scenarios_dir = tmp_path / "scenarios"
    room_dir = rooms_dir / "room-1"
    room_dir.mkdir(parents=True)
    scenarios_dir.mkdir()

    context = build_agent_context(
        room_id="room-1",
        rooms_dir=rooms_dir,
        scenarios_dir=scenarios_dir,
        user_id=7,
        agent_id="kp",
    )

    assert context.room_id == "room-1"
    assert context.room_dir == room_dir
    assert context.scenarios_dir == scenarios_dir
    assert context.user_id == 7


def test_runtime_retries_once_when_trigger_tool_is_followed_by_empty_completion():
    class EmptyAfterToolRequester:
        def __init__(self):
            self.calls = []

        def __call__(self, payload):
            self.calls.append(payload)
            if len(self.calls) == 1:
                return {"choices": [{"message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call-trigger",
                        "type": "function",
                        "function": {"name": "test.trigger", "arguments": "{}"},
                    }],
                }}]}
            if len(self.calls) == 2:
                return {"choices": [{"message": {"role": "assistant", "content": ""}}]}
            return {"choices": [{"message": {"role": "assistant", "content": "KP continued"}}]}

    requester = EmptyAfterToolRequester()
    tool = AgentTool(
        name="test.trigger",
        description="Reveal trigger",
        parameters={"type": "object", "properties": {}},
        handler=lambda arguments, context: {"direct_message": {"type": "trigger", "content": "secret"}},
    )

    result = run_agent_completion(
        requester=requester,
        base_payload={"model": "fake-model", "messages": [{"role": "user", "content": "check"}]},
        profile=AgentProfile(id="kp", name="KP", prompt="prompt", tool_names=["test.trigger"]),
        registry=ToolRegistry([tool]),
        context=AgentRequestContext(room_id="room-1"),
    )

    assert len(requester.calls) == 3
    assert result.content == "KP continued"
