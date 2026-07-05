from trpg_server.agents.context import AgentRequestContext
from trpg_server.agents.profiles import AgentProfile
from trpg_server.agents.runtime import run_agent_completion
from trpg_server.agents.tools.base import AgentTool, ToolRegistry


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
