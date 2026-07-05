# Modular Agent Runtime and KP Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular room-aware AI agent runtime, with KP as the first agent profile using scenario, character, memory, and COC7 dice-check tools.

**Architecture:** Add `trpg_server/agents/` as a generic runtime layer. The chat route resolves an agent profile, passes request context to the runtime, and the runtime executes only the tools enabled for that profile. KP-specific behavior lives in `data/config/roles/kp.md` plus default KP tool registration, so future agents can use different prompts and tool sets.

**Tech Stack:** Python 3, Flask, pytest, `requests`, JSON file stores, TOML-like config parsing, TypeScript frontend settings UI.

---

## File Structure

- Create `trpg_server/agents/__init__.py`: package exports.
- Create `trpg_server/agents/config.py`: read AI runtime options from `general.toml`.
- Create `trpg_server/agents/profiles.py`: normalize role configs into agent profiles and default KP tools.
- Create `trpg_server/agents/context.py`: immutable request context object and room/scenario loading helpers.
- Create `trpg_server/agents/runtime.py`: OpenAI-compatible request loop and tool-call execution.
- Create `trpg_server/agents/memory.py`: room-scoped memory read/write helpers.
- Create `trpg_server/agents/tools/__init__.py`: tool registration exports.
- Create `trpg_server/agents/tools/base.py`: `AgentTool`, `ToolRegistry`, schema helpers, validation errors.
- Create `trpg_server/agents/tools/dice.py`: backend dice roller and COC7 percentile check tool.
- Create `trpg_server/agents/tools/room.py`: scenario context, character card, and memory tools.
- Modify `trpg_server/routes/chat.py`: delegate AI calls to agent runtime while preserving response shape.
- Modify `data/config/roles/kp.md`: replace broken mojibake prompt with valid UTF-8 Chinese KP prompt.
- Modify `data/config/general.toml`: add `[ai] stream_output = false`.
- Modify `frontend/src/index/fragments/03-room-tools-auth-settings.html`: add AI streaming checkbox.
- Modify `frontend/src/js/config/ConfigManager.ts`: load and save the AI streaming setting in config state.
- Modify `frontend/src/js/tabs.ts`: bind general settings fields so the stream flag persists.
- Add `tests/test_agent_profiles.py`: profile and config tests.
- Add `tests/test_agent_tools.py`: dice, room context, character card, and memory tests.
- Add `tests/test_agent_runtime.py`: tool loop and authorization tests.
- Add `tests/test_kp_prompt_and_stream_config.py`: prompt integrity and frontend setting tests.

---

### Task 1: Agent Profile and AI Config Foundation

**Files:**
- Create: `trpg_server/agents/__init__.py`
- Create: `trpg_server/agents/config.py`
- Create: `trpg_server/agents/profiles.py`
- Test: `tests/test_agent_profiles.py`

- [ ] **Step 1: Write failing profile/config tests**

Add `tests/test_agent_profiles.py`:

```python
import json
from pathlib import Path

from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.agents.profiles import DEFAULT_KP_TOOLS, resolve_agent_profile


def test_kp_profile_gets_default_tools_when_role_has_none(tmp_path):
    prompt_file = tmp_path / "kp.md"
    prompt_file.write_text("你是KP。", encoding="utf-8")
    role = {
        "id": "kp",
        "name": "KP",
        "prompt": "你是KP。",
        "provider": "openrouter",
        "wake_words": ["@KP"],
    }

    profile = resolve_agent_profile(role, prompt_file=prompt_file)

    assert profile.id == "kp"
    assert profile.name == "KP"
    assert profile.provider == "openrouter"
    assert profile.prompt == "你是KP。"
    assert profile.tool_names == DEFAULT_KP_TOOLS
    assert profile.wake_words == ["@KP"]


def test_non_kp_profile_defaults_to_no_tools(tmp_path):
    prompt_file = tmp_path / "kp.md"
    prompt_file.write_text("你是KP。", encoding="utf-8")
    profile = resolve_agent_profile(
        {
            "id": "narrator",
            "name": "Narrator",
            "prompt": "旁白。",
            "provider": "lmstudio",
        },
        prompt_file=prompt_file,
    )

    assert profile.id == "narrator"
    assert profile.tool_names == []


def test_role_can_explicitly_select_tools(tmp_path):
    prompt_file = tmp_path / "kp.md"
    prompt_file.write_text("你是KP。", encoding="utf-8")
    profile = resolve_agent_profile(
        {
            "id": "rules",
            "name": "Rules Helper",
            "prompt": "规则助手。",
            "tools": ["dice.roll_coc_check"],
            "context": ["room.recent_messages"],
        },
        prompt_file=prompt_file,
    )

    assert profile.tool_names == ["dice.roll_coc_check"]
    assert profile.context_providers == ["room.recent_messages"]


def test_ai_runtime_config_reads_stream_flag(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "general.toml").write_text("[ai]\nstream_output = true\n", encoding="utf-8")

    config = load_ai_runtime_config(config_dir)

    assert config.stream_output is True
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_agent_profiles.py -v
```

Expected: import failure for `trpg_server.agents`.

- [ ] **Step 3: Implement minimal package and profile/config code**

Create `trpg_server/agents/__init__.py`:

```python
"""Agent runtime package for AI-controlled TRPG assistants."""
```

Create `trpg_server/agents/config.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AIRuntimeConfig:
    stream_output: bool = False


def load_ai_runtime_config(config_dir: Path) -> AIRuntimeConfig:
    general_file = Path(config_dir) / "general.toml"
    if not general_file.exists():
        return AIRuntimeConfig()

    current_section = ""
    stream_output = False
    for raw_line in general_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip()
            continue
        if current_section == "ai" and "=" in line:
            key, value = [part.strip() for part in line.split("=", 1)]
            if key == "stream_output":
                stream_output = value.lower() == "true"
    return AIRuntimeConfig(stream_output=stream_output)
```

Create `trpg_server/agents/profiles.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_KP_TOOLS = [
    "room.get_scenario_context",
    "room.get_character_cards",
    "room.get_memory",
    "room.remember_fact",
    "dice.roll_coc_check",
]


@dataclass(frozen=True)
class AgentProfile:
    id: str
    name: str
    prompt: str
    provider: str | None = None
    wake_words: list[str] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)
    context_providers: list[str] = field(default_factory=list)


def resolve_agent_profile(role: dict[str, Any], prompt_file: Path) -> AgentProfile:
    role_id = str(role.get("id") or "kp")
    prompt = str(role.get("prompt") or "")
    if role_id == "kp" and not prompt and prompt_file.exists():
        prompt = prompt_file.read_text(encoding="utf-8")

    configured_tools = role.get("tools")
    if isinstance(configured_tools, list):
        tool_names = [str(name) for name in configured_tools if str(name).strip()]
    elif role_id == "kp":
        tool_names = DEFAULT_KP_TOOLS.copy()
    else:
        tool_names = []

    configured_context = role.get("context")
    context_providers = (
        [str(name) for name in configured_context if str(name).strip()]
        if isinstance(configured_context, list)
        else []
    )

    return AgentProfile(
        id=role_id,
        name=str(role.get("name") or role_id),
        prompt=prompt,
        provider=role.get("provider"),
        wake_words=[str(word) for word in role.get("wake_words", [])],
        tool_names=tool_names,
        context_providers=context_providers,
    )
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
pytest tests/test_agent_profiles.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_agent_profiles.py trpg_server/agents/__init__.py trpg_server/agents/config.py trpg_server/agents/profiles.py
git commit -m "feat: add agent profile foundation"
```

---

### Task 2: Backend COC7 Dice Tool

**Files:**
- Create: `trpg_server/agents/tools/__init__.py`
- Create: `trpg_server/agents/tools/base.py`
- Create: `trpg_server/agents/tools/dice.py`
- Test: `tests/test_agent_tools.py`

- [ ] **Step 1: Write failing dice tests**

Add the first section to `tests/test_agent_tools.py`:

```python
from trpg_server.agents.tools.dice import roll_coc_check


def test_coc_check_regular_success_with_fixed_rng():
    result = roll_coc_check(
        {
            "skill": "锁匠",
            "target": 45,
            "difficulty": "regular",
            "reason": "打开地下室门锁",
        },
        rng=lambda sides: 34,
    )

    assert result["roll"] == 34
    assert result["target"] == 45
    assert result["threshold"] == 45
    assert result["success"] is True
    assert result["success_level"] == "regular"
    assert "锁匠" in result["summary"]


def test_coc_check_hard_failure_uses_half_threshold():
    result = roll_coc_check(
        {"skill": "侦查", "target": 50, "difficulty": "hard"},
        rng=lambda sides: 31,
    )

    assert result["threshold"] == 25
    assert result["success"] is False
    assert result["success_level"] == "failure"


def test_coc_check_extreme_success_uses_fifth_threshold():
    result = roll_coc_check(
        {"skill": "图书馆使用", "target": 80, "difficulty": "extreme"},
        rng=lambda sides: 16,
    )

    assert result["threshold"] == 16
    assert result["success"] is True
    assert result["success_level"] == "extreme"


def test_coc_check_rejects_invalid_target():
    result = roll_coc_check({"skill": "锁匠", "target": 0}, rng=lambda sides: 1)

    assert result["error"] == "target must be between 1 and 100"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_agent_tools.py -v
```

Expected: import failure for `trpg_server.agents.tools.dice`.

- [ ] **Step 3: Implement tool base and dice code**

Create `trpg_server/agents/tools/base.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class ToolExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any], Any], dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self, tools: list[AgentTool] | None = None):
        self._tools = {tool.name: tool for tool in tools or []}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def select(self, names: list[str]) -> list[AgentTool]:
        return [self._tools[name] for name in names if name in self._tools]

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)
```

Create `trpg_server/agents/tools/dice.py`:

```python
import random
from typing import Any, Callable

from trpg_server.agents.tools.base import AgentTool


def _as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _threshold(target: int, difficulty: str) -> int:
    if difficulty == "hard":
        return target // 2
    if difficulty == "extreme":
        return target // 5
    return target


def _success_level(roll: int, target: int) -> str:
    if roll == 1:
        return "critical"
    if roll <= target // 5:
        return "extreme"
    if roll <= target // 2:
        return "hard"
    if roll <= target:
        return "regular"
    if roll >= 96 and target < 50:
        return "fumble"
    if roll == 100:
        return "fumble"
    return "failure"


def roll_coc_check(arguments: dict[str, Any], rng: Callable[[int], int] | None = None) -> dict[str, Any]:
    roller = rng or (lambda sides: random.randint(1, sides))
    target = _as_int(arguments.get("target"))
    if target < 1 or target > 100:
        return {"error": "target must be between 1 and 100"}

    difficulty = str(arguments.get("difficulty") or "regular").lower()
    if difficulty not in {"regular", "hard", "extreme"}:
        return {"error": "difficulty must be regular, hard, or extreme"}

    roll = roller(100)
    threshold = _threshold(target, difficulty)
    level = _success_level(roll, target)
    success = roll <= threshold or level == "critical"
    if level == "fumble":
        success = False

    skill = str(arguments.get("skill") or "检定")
    reason = str(arguments.get("reason") or "")
    summary = f"{skill}检定：1d100={roll}，目标{target}，{difficulty}难度阈值{threshold}，结果：{level}。"
    if reason:
        summary += f" 原因：{reason}。"

    return {
        "skill": skill,
        "reason": reason,
        "roll": roll,
        "target": target,
        "difficulty": difficulty,
        "threshold": threshold,
        "success": success,
        "success_level": level if success else "failure",
        "raw_success_level": level,
        "critical": roll == 1,
        "fumble": level == "fumble",
        "summary": summary,
    }


def execute_roll_coc_check(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    return roll_coc_check(arguments)


ROLL_COC_CHECK_TOOL = AgentTool(
    name="dice.roll_coc_check",
    description="Roll a real backend COC7 percentile check. The model must not invent dice results.",
    parameters={
        "type": "object",
        "properties": {
            "character_name": {"type": "string"},
            "skill": {"type": "string"},
            "target": {"type": "integer", "minimum": 1, "maximum": 100},
            "difficulty": {"type": "string", "enum": ["regular", "hard", "extreme"]},
            "reason": {"type": "string"},
        },
        "required": ["skill", "target"],
    },
    handler=execute_roll_coc_check,
)
```

Create `trpg_server/agents/tools/__init__.py`:

```python
from trpg_server.agents.tools.base import AgentTool, ToolRegistry
from trpg_server.agents.tools.dice import ROLL_COC_CHECK_TOOL


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry([ROLL_COC_CHECK_TOOL])
```

- [ ] **Step 4: Run dice tests**

Run:

```powershell
pytest tests/test_agent_tools.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_agent_tools.py trpg_server/agents/tools
git commit -m "feat: add backend coc7 dice tool"
```

---

### Task 3: Room Context and Memory Tools

**Files:**
- Create: `trpg_server/agents/context.py`
- Create: `trpg_server/agents/memory.py`
- Modify: `trpg_server/agents/tools/room.py`
- Modify: `trpg_server/agents/tools/__init__.py`
- Test: `tests/test_agent_tools.py`

- [ ] **Step 1: Add failing room tool tests**

Append to `tests/test_agent_tools.py`:

```python
import json

from trpg_server.agents.context import AgentRequestContext
from trpg_server.agents.memory import read_room_memory, remember_room_fact
from trpg_server.agents.tools.room import get_room_character_cards, get_room_scenario_context


def test_room_scenario_context_loads_current_room_scenario(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps({"id": "room-1", "scenario_id": 7, "members": []}),
        encoding="utf-8",
    )
    (scenarios_dir / "haunted.json").write_text(
        json.dumps(
            {
                "id": 7,
                "title": "雨夜来客",
                "description": "暴雨中的宅邸调查。",
                "scenes": [{"id": "hall", "title": "门厅", "description": "潮湿的地毯。"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir, scenarios_dir=scenarios_dir)

    result = get_room_scenario_context({"query": "门厅"}, context)

    assert result["scenario"]["title"] == "雨夜来客"
    assert result["matches"][0]["title"] == "门厅"


def test_room_character_cards_returns_active_bound_cards(tmp_path):
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    (room_dir / "info.json").write_text(
        json.dumps(
            {
                "id": "room-1",
                "members": [
                    {
                        "user_id": 1,
                        "username": "alice",
                        "status": "active",
                        "character_card": {
                            "id": "investigator",
                            "name": "林见山",
                            "background": {"story": "失踪记者。"},
                            "skills": [{"name": "锁匠", "value": 45}],
                        },
                        "character_state": {"current_hp": 10, "current_san": 55},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir)

    result = get_room_character_cards({}, context)

    assert result["members"][0]["username"] == "alice"
    assert result["members"][0]["character_card"]["name"] == "林见山"
    assert result["members"][0]["character_state"]["current_san"] == 55


def test_room_memory_write_and_read(tmp_path):
    room_dir = tmp_path / "rooms" / "room-1"
    room_dir.mkdir(parents=True)
    context = AgentRequestContext(room_id="room-1", room_dir=room_dir, agent_id="kp")

    remembered = remember_room_fact(
        {"kind": "npc_state", "content": "图书管理员开始怀疑调查员。", "importance": 3},
        context,
    )
    memory = read_room_memory({"query": "图书管理员", "limit": 5}, context)

    assert remembered["stored"] is True
    assert memory["items"][0]["content"] == "图书管理员开始怀疑调查员。"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_agent_tools.py -v
```

Expected: import failure for `trpg_server.agents.context`.

- [ ] **Step 3: Implement context and memory helpers**

Create `trpg_server/agents/context.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trpg_server.json_store import read_json


@dataclass(frozen=True)
class AgentRequestContext:
    room_id: str | None = None
    room_dir: Path | None = None
    scenarios_dir: Path | None = None
    user_id: str | int | None = None
    agent_id: str = "kp"

    def room_info(self) -> dict[str, Any]:
        if not self.room_dir:
            return {}
        return read_json(self.room_dir / "info.json", default={})

    def room_messages(self) -> list[dict[str, Any]]:
        if not self.room_dir:
            return []
        return read_json(self.room_dir / "messages.json", default=[])
```

Create `trpg_server/agents/memory.py`:

```python
import time
from uuid import uuid4
from typing import Any

from trpg_server.json_store import read_json, write_json_atomic

MAX_MEMORY_ITEMS = 200
MAX_MEMORY_CONTENT_LENGTH = 1000


def _memory_file(context: Any):
    if not context.room_dir:
        raise ValueError("room context is required for memory")
    return context.room_dir / "agent_memory.json"


def remember_room_fact(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    content = str(arguments.get("content") or "").strip()
    if not content:
        return {"error": "content is required"}
    item = {
        "id": uuid4().hex,
        "agent_id": getattr(context, "agent_id", "kp"),
        "kind": str(arguments.get("kind") or "fact")[:80],
        "content": content[:MAX_MEMORY_CONTENT_LENGTH],
        "importance": max(1, min(5, int(arguments.get("importance") or 1))),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = _memory_file(context)
    memory = read_json(path, default=[])
    memory.insert(0, item)
    write_json_atomic(path, memory[:MAX_MEMORY_ITEMS])
    return {"stored": True, "item": item}


def read_room_memory(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    path = _memory_file(context)
    query = str(arguments.get("query") or "").strip()
    limit = max(1, min(50, int(arguments.get("limit") or 10)))
    memory = read_json(path, default=[])
    if query:
        memory = [item for item in memory if query in str(item.get("content", "")) or query in str(item.get("kind", ""))]
    memory.sort(key=lambda item: (int(item.get("importance") or 1), item.get("created_at", "")), reverse=True)
    return {"items": memory[:limit]}
```

- [ ] **Step 4: Implement room tools and register them**

Create `trpg_server/agents/tools/room.py`:

```python
import json
from typing import Any

from trpg_server.agents.memory import read_room_memory, remember_room_fact
from trpg_server.agents.tools.base import AgentTool
from trpg_server.json_store import read_json


def _find_scenario(scenarios_dir, scenario_id):
    if not scenarios_dir or scenario_id is None or not scenarios_dir.exists():
        return None
    for path in scenarios_dir.glob("*.json"):
        scenario = read_json(path, default={})
        if str(scenario.get("id")) == str(scenario_id):
            return scenario
    return None


def _matches_query(value: Any, query: str) -> bool:
    if not query:
        return True
    return query.casefold() in json.dumps(value, ensure_ascii=False).casefold()


def get_room_scenario_context(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    info = context.room_info()
    scenario = _find_scenario(context.scenarios_dir, info.get("scenario_id"))
    if not scenario:
        return {"scenario": None, "matches": [], "message": "current room scenario was not found"}

    query = str(arguments.get("query") or "").strip()
    scene_id = str(arguments.get("scene_id") or "").strip()
    max_items = max(1, min(20, int(arguments.get("max_items") or 5)))
    candidates = []
    for key in ("scenes", "locations", "npcs", "clues"):
        values = scenario.get(key)
        if isinstance(values, list):
            for item in values:
                if scene_id and str(item.get("id", "")) != scene_id:
                    continue
                if _matches_query(item, query):
                    candidates.append({"section": key, **item})
    return {
        "scenario": {
            "id": scenario.get("id"),
            "title": scenario.get("title"),
            "description": scenario.get("description"),
        },
        "matches": candidates[:max_items],
    }


def get_room_character_cards(arguments: dict[str, Any], context: Any) -> dict[str, Any]:
    include_inactive = bool(arguments.get("include_inactive", False))
    members = []
    for member in context.room_info().get("members", []):
        active = member.get("is_active", True) is not False and member.get("status", "active") != "removed"
        if not include_inactive and not active:
            continue
        members.append(
            {
                "user_id": member.get("user_id"),
                "username": member.get("username"),
                "active": active,
                "character_card": member.get("character_card"),
                "character_state": member.get("character_state"),
            }
        )
    return {"members": members}


GET_SCENARIO_CONTEXT_TOOL = AgentTool(
    name="room.get_scenario_context",
    description="Load scenario scenes, NPCs, clues, and locations for the current room.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "scene_id": {"type": "string"},
            "max_items": {"type": "integer", "minimum": 1, "maximum": 20},
        },
    },
    handler=get_room_scenario_context,
)

GET_CHARACTER_CARDS_TOOL = AgentTool(
    name="room.get_character_cards",
    description="Load character cards and HP/SAN state for current room members.",
    parameters={"type": "object", "properties": {"include_inactive": {"type": "boolean"}}},
    handler=get_room_character_cards,
)

GET_MEMORY_TOOL = AgentTool(
    name="room.get_memory",
    description="Read remembered facts for the current room.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}},
    handler=read_room_memory,
)

REMEMBER_FACT_TOOL = AgentTool(
    name="room.remember_fact",
    description="Persist an important room fact for future KP continuity.",
    parameters={
        "type": "object",
        "properties": {
            "kind": {"type": "string"},
            "content": {"type": "string"},
            "importance": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["content"],
    },
    handler=remember_room_fact,
)
```

Modify `trpg_server/agents/tools/__init__.py`:

```python
from trpg_server.agents.tools.base import AgentTool, ToolRegistry
from trpg_server.agents.tools.dice import ROLL_COC_CHECK_TOOL
from trpg_server.agents.tools.room import (
    GET_CHARACTER_CARDS_TOOL,
    GET_MEMORY_TOOL,
    GET_SCENARIO_CONTEXT_TOOL,
    REMEMBER_FACT_TOOL,
)


def default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            GET_SCENARIO_CONTEXT_TOOL,
            GET_CHARACTER_CARDS_TOOL,
            GET_MEMORY_TOOL,
            REMEMBER_FACT_TOOL,
            ROLL_COC_CHECK_TOOL,
        ]
    )
```

- [ ] **Step 5: Run room tool tests**

Run:

```powershell
pytest tests/test_agent_tools.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```powershell
git add tests/test_agent_tools.py trpg_server/agents/context.py trpg_server/agents/memory.py trpg_server/agents/tools
git commit -m "feat: add room context tools and memory"
```

---

### Task 4: Generic Agent Runtime Tool Loop

**Files:**
- Create: `trpg_server/agents/runtime.py`
- Test: `tests/test_agent_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

Add `tests/test_agent_runtime.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_agent_runtime.py -v
```

Expected: import failure for `trpg_server.agents.runtime`.

- [ ] **Step 3: Implement runtime**

Create `trpg_server/agents/runtime.py`:

```python
import json
from dataclasses import dataclass
from typing import Any, Callable

from trpg_server.agents.profiles import AgentProfile
from trpg_server.agents.tools.base import ToolRegistry


@dataclass(frozen=True)
class AgentCompletionResult:
    content: str = ""
    token_count: int | None = None
    error: str | None = None
    response_data: dict[str, Any] | None = None


def _extract_message(response_data: dict[str, Any]) -> dict[str, Any]:
    choices = response_data.get("choices", [])
    if not choices:
        return {}
    return choices[0].get("message") or choices[0].get("delta") or {}


def _extract_token_count(response_data: dict[str, Any]) -> int | None:
    usage = response_data.get("usage") or {}
    if "total_tokens" in usage:
        return usage["total_tokens"]
    if "completion_tokens" in usage and "prompt_tokens" in usage:
        return usage["completion_tokens"] + usage["prompt_tokens"]
    return None


def _parse_arguments(raw_arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not raw_arguments:
        return {}
    return json.loads(raw_arguments)


def _tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(message.get("tool_calls"), list):
        return message["tool_calls"]
    function_call = message.get("function_call")
    if isinstance(function_call, dict):
        return [{"id": "function-call", "type": "function", "function": function_call}]
    return []


def run_agent_completion(
    requester: Callable[[dict[str, Any]], dict[str, Any]],
    base_payload: dict[str, Any],
    profile: AgentProfile,
    registry: ToolRegistry,
    context: Any,
    max_tool_rounds: int = 4,
) -> AgentCompletionResult:
    payload = {**base_payload}
    messages = list(payload.get("messages", []))
    payload["messages"] = messages
    enabled_tools = registry.select(profile.tool_names)
    if enabled_tools:
        payload["tools"] = [tool.schema() for tool in enabled_tools]
        payload["tool_choice"] = "auto"

    enabled_by_name = {tool.name: tool for tool in enabled_tools}
    last_response = None

    for _round in range(max_tool_rounds + 1):
        response_data = requester(payload)
        last_response = response_data
        message = _extract_message(response_data)
        calls = _tool_calls(message)
        if not calls:
            return AgentCompletionResult(
                content=str(message.get("content") or ""),
                token_count=_extract_token_count(response_data),
                response_data=response_data,
            )

        messages.append(message)
        for call in calls:
            function = call.get("function") or {}
            tool_name = str(function.get("name") or "")
            tool = enabled_by_name.get(tool_name)
            if not tool:
                return AgentCompletionResult(error=f"Tool {tool_name} is not enabled for agent {profile.id}")
            try:
                arguments = _parse_arguments(function.get("arguments"))
                result = tool.handler(arguments, context)
            except Exception as exc:
                result = {"error": str(exc)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id") or tool_name,
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return AgentCompletionResult(error="Agent tool loop limit exceeded", response_data=last_response)
```

- [ ] **Step 4: Run runtime tests**

Run:

```powershell
pytest tests/test_agent_runtime.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_agent_runtime.py trpg_server/agents/runtime.py
git commit -m "feat: add agent tool runtime"
```

---

### Task 5: Chat Route Integration

**Files:**
- Modify: `trpg_server/routes/chat.py`
- Test: `tests/test_agent_runtime.py`
- Test: `tests/test_agent_profiles.py`

- [ ] **Step 1: Add integration tests for room context construction**

Append to `tests/test_agent_runtime.py`:

```python
from pathlib import Path

from trpg_server.agents.context import build_agent_context


def test_build_agent_context_resolves_room_dir_and_scenarios_dir(tmp_path):
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
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_agent_runtime.py::test_build_agent_context_resolves_room_dir_and_scenarios_dir -v
```

Expected: import failure for `build_agent_context`.

- [ ] **Step 3: Add context builder**

Modify `trpg_server/agents/context.py`:

```python
from trpg_server.security import safe_join


def build_agent_context(room_id, rooms_dir, scenarios_dir, user_id=None, agent_id="kp") -> AgentRequestContext:
    room_dir = safe_join(rooms_dir, room_id) if room_id else None
    return AgentRequestContext(
        room_id=str(room_id) if room_id else None,
        room_dir=room_dir,
        scenarios_dir=scenarios_dir,
        user_id=user_id,
        agent_id=agent_id,
    )
```

- [ ] **Step 4: Refactor chat route to use runtime**

In `trpg_server/routes/chat.py`:

- Import the new modules:

```python
from trpg_server.agents.config import load_ai_runtime_config
from trpg_server.agents.context import build_agent_context
from trpg_server.agents.profiles import resolve_agent_profile
from trpg_server.agents.runtime import run_agent_completion
from trpg_server.agents.tools import default_tool_registry
from trpg_server.settings import CONFIG_DIR, HISTORY_DIR, ROOMS_DIR, SCENARIOS_DIR
```

- Add helper:

```python
def _post_ai_request(base_url, headers):
    def requester(payload):
        response = requests.post(base_url, headers=headers, json=payload, timeout=300)
        if not response.ok:
            raise RuntimeError(f"API request failed: {response.status_code}")
        return response.json()
    return requester
```

- In `chat()`, replace direct `requests.post` response handling with:

```python
        room_id = message_data.get("room_id")
        agent_profile = resolve_agent_profile(role_config, _get_kp_prompt_file())
        runtime_config = load_ai_runtime_config(_get_config_dir())
        request_data = {
            "messages": _build_messages(agent_profile.prompt or _load_kp_prompt(), history, content),
            "model": _select_model(platform_config),
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        if runtime_config.stream_output:
            request_data["stream"] = False

        agent_context = build_agent_context(
            room_id=room_id,
            rooms_dir=current_app.config.get("ROOMS_DIR", ROOMS_DIR),
            scenarios_dir=current_app.config.get("SCENARIOS_DIR", SCENARIOS_DIR),
            user_id=user_id,
            agent_id=agent_profile.id,
        )
        result = run_agent_completion(
            requester=_post_ai_request(base_url, headers),
            base_payload=request_data,
            profile=agent_profile,
            registry=default_tool_registry(),
            context=agent_context,
        )
        if result.error:
            return error_response("AI agent request failed", 500, result.error)
        ai_response = result.content
        token_count = result.token_count
```

Keep the existing history persistence and `success_response` shape.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
pytest tests/test_agent_profiles.py tests/test_agent_runtime.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add trpg_server/routes/chat.py trpg_server/agents/context.py tests/test_agent_runtime.py
git commit -m "feat: route chat through agent runtime"
```

---

### Task 6: KP Prompt Rewrite

**Files:**
- Modify: `data/config/roles/kp.md`
- Test: `tests/test_kp_prompt_and_stream_config.py`

- [ ] **Step 1: Write failing prompt integrity test**

Add `tests/test_kp_prompt_and_stream_config.py`:

```python
from pathlib import Path


def test_kp_prompt_is_valid_chinese_and_requires_tools_for_dice():
    prompt = Path("data/config/roles/kp.md").read_text(encoding="utf-8")

    assert "浣犳槸" not in prompt
    assert "你是KP" in prompt
    assert "COC7" in prompt
    assert "不得编造骰点" in prompt
    assert "dice.roll_coc_check" in prompt
    assert "不无故让调查员死亡" in prompt
    assert "失败归因" in prompt
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
pytest tests/test_kp_prompt_and_stream_config.py::test_kp_prompt_is_valid_chinese_and_requires_tools_for_dice -v
```

Expected: failure because current `kp.md` contains mojibake.

- [ ] **Step 3: Replace KP prompt with valid UTF-8 Chinese**

Write `data/config/roles/kp.md` with this structure:

```markdown
# KP 系统提示词

你是KP（Keeper），负责主持以《克苏鲁的呼唤》第七版（COC7）规则为基础的 TRPG 房间。

## 核心职责

1. 维护公平、紧张、可理解的调查体验。
2. 严格遵守 COC7 规则，不为了戏剧效果篡改检定、伤害、理智损失或死亡后果。
3. 保护玩家能动性：不要替玩家做决定，不要提前揭露玩家角色不可能知道的信息。
4. 让每位玩家都有清晰的参与机会、线索接触机会和角色高光时刻。
5. 不无故让调查员死亡。死亡、永久损伤、重大理智崩溃必须来自明确规则、明确风险和叙事因果。

## 工具调用规则

- 当你需要当前房间剧本、场景、NPC、线索或地点信息时，调用 `room.get_scenario_context`。
- 当你需要玩家角色卡、属性、技能、背景、装备、HP/SAN 状态时，调用 `room.get_character_cards`。
- 当你需要保持长期一致性的房间事实时，调用 `room.remember_fact`。
- 当你需要回忆已记录的房间事实时，调用 `room.get_memory`。
- 当行动存在 COC7 规则意义上的不确定性并需要检定时，必须调用 `dice.roll_coc_check`。
- 不得编造骰点、检定结果、成功等级、伤害或理智损失。没有工具结果时，不要声称已经完成投骰。

## 检定与失败处理

1. 只在结果有意义、风险清晰或规则要求时要求检定。
2. 根据 COC7 判定普通、困难、极难、奖励骰、惩罚骰、大成功和大失败。
3. 检定失败时，优先将原因归因于世界阻力、环境复杂、工具损坏、时间压力、外部干扰或信息本身不可靠，而不是贬低玩家或角色能力。
4. 失败仍应推动故事。失败可以带来代价、延迟、暴露、资源消耗、误导线索或新的危险，但不要让故事停止。
5. 在规则允许的范围内维持玩家体验，不用羞辱性语言描述失败。

## 叙事风格

- 使用第二人称描述玩家直接感知到的景象。
- 展示而非直接告知：用气味、声音、触感、光线、迟疑和异常细节呈现恐怖。
- 保持秘密，不主动透露幕后真相。
- NPC 有动机、恐惧、秘密和行动节奏，会因玩家行为产生连锁反应。
- 对玩家创意优先使用“可以，而且……”或“可以，但是……”，再给出规则后果。

## 规则底线

- 严格遵守 COC7 的技能检定、对抗检定、理智检定、战斗、追逐、伤势和成长规则。
- 叙事可以灵活，规则结果不能伪造。
- 角色卡、房间状态、剧本数据和工具返回结果优先于你的记忆。
- 如果记忆与房间或剧本数据冲突，以房间和剧本数据为准。
```

- [ ] **Step 4: Run prompt test**

Run:

```powershell
pytest tests/test_kp_prompt_and_stream_config.py::test_kp_prompt_is_valid_chinese_and_requires_tools_for_dice -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```powershell
git add data/config/roles/kp.md tests/test_kp_prompt_and_stream_config.py
git commit -m "feat: rewrite kp prompt with tool rules"
```

---

### Task 7: Streaming Setting in Config and UI

**Files:**
- Modify: `data/config/general.toml`
- Modify: `frontend/src/index/fragments/03-room-tools-auth-settings.html`
- Modify: `frontend/src/js/config/ConfigManager.ts`
- Modify: `frontend/src/js/tabs.ts`
- Test: `tests/test_kp_prompt_and_stream_config.py`

- [ ] **Step 1: Add failing stream setting tests**

Append to `tests/test_kp_prompt_and_stream_config.py`:

```python
def test_general_config_contains_ai_stream_output_flag():
    general_config = Path("data/config/general.toml").read_text(encoding="utf-8")

    assert "[ai]" in general_config
    assert "stream_output = false" in general_config


def test_frontend_settings_exposes_ai_stream_output_toggle():
    settings_html = Path("frontend/src/index/fragments/03-room-tools-auth-settings.html").read_text(encoding="utf-8")
    config_source = Path("frontend/src/js/config/ConfigManager.ts").read_text(encoding="utf-8")
    tabs_source = Path("frontend/src/js/tabs.ts").read_text(encoding="utf-8")

    assert 'id="streamOutput"' in settings_html
    assert "stream_output" in config_source
    assert "streamOutput" in tabs_source
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
pytest tests/test_kp_prompt_and_stream_config.py -v
```

Expected: stream setting tests fail.

- [ ] **Step 3: Add config flag**

Modify `data/config/general.toml`:

```toml
[ai]
stream_output = false
```

Place it after `[chat]` so chat/AI behavior stays grouped.

- [ ] **Step 4: Add settings checkbox**

In `frontend/src/index/fragments/03-room-tools-auth-settings.html`, inside the “聊天设置” block after `showTimestamp`, add:

```html
<div class="form-group mt-2">
    <div class="form-check">
        <input type="checkbox" class="form-check-input" id="streamOutput">
        <label class="form-check-label" for="streamOutput">启用 AI 流式输出</label>
    </div>
</div>
```

- [ ] **Step 5: Load config into UI**

Modify `frontend/src/js/config/ConfigManager.ts` in `applyGeneralSettings()`:

```ts
configSetCheckboxValue("streamOutput", this.get("general", "ai", "stream_output", false));
```

Place it after `showTimestamp`.

- [ ] **Step 6: Persist general setting changes**

Modify `frontend/src/js/tabs.ts` by adding a helper after `initSettingsTabs()`:

```ts
function bindGeneralCheckboxSetting(elementId: string, sectionName: string, key: string): void {
    const input = document.getElementById(elementId) as HTMLInputElement | null;
    if (!input) return;
    input.addEventListener("change", async () => {
        const generalConfig = configManager.getConfig("general");
        const section = isConfigObject(generalConfig[sectionName]) ? generalConfig[sectionName] : {};
        section[key] = input.checked;
        generalConfig[sectionName] = section;
        await configManager.saveConfig("general", generalConfig);
    });
}
```

Call it in `initSettingsTabs()`:

```ts
bindGeneralCheckboxSetting("streamOutput", "ai", "stream_output");
```

- [ ] **Step 7: Run Python and TypeScript checks**

Run:

```powershell
pytest tests/test_kp_prompt_and_stream_config.py -v
npm run typecheck
```

Expected: pytest passes and TypeScript reports no errors.

- [ ] **Step 8: Commit**

```powershell
git add data/config/general.toml frontend/src/index/fragments/03-room-tools-auth-settings.html frontend/src/js/config/ConfigManager.ts frontend/src/js/tabs.ts tests/test_kp_prompt_and_stream_config.py
git commit -m "feat: add ai stream output setting"
```

---

### Task 8: Full Verification and Build Output

**Files:**
- Modify only files changed by build if the repository expects generated frontend output.

- [ ] **Step 1: Run focused backend tests**

Run:

```powershell
pytest tests/test_agent_profiles.py tests/test_agent_tools.py tests/test_agent_runtime.py tests/test_kp_prompt_and_stream_config.py -v
```

Expected: all selected tests pass.

- [ ] **Step 2: Run existing backend test suite**

Run:

```powershell
pytest tests -v
```

Expected: all tests pass. If existing unrelated tests fail because of current mojibake assertions in older files, capture the exact failures and do not hide them.

- [ ] **Step 3: Run frontend checks and build**

Run:

```powershell
npm run typecheck
npm run build:frontend
```

Expected: TypeScript passes and frontend build completes.

- [ ] **Step 4: Inspect final git diff**

Run:

```powershell
git status --short
git diff --stat
```

Expected: only files from this plan plus generated frontend output if produced by `npm run build:frontend`.

- [ ] **Step 5: Commit final build output if changed**

If `frontend/dist/index.html` or generated frontend files changed due to the build, commit them separately:

```powershell
git add frontend/dist/index.html frontend/src/js/generated/templates.ts
git commit -m "build: refresh frontend assets"
```

If no generated files changed, skip this commit.

---

## Self-Review

Spec coverage:

- Modular runtime: Tasks 1, 4, and 5.
- Future agents with different prompts/tools: Task 1 profile contract and Task 4 registry authorization.
- Scenario and character context: Task 3.
- COC7 backend dice tool: Task 2.
- Memory read/write: Task 3.
- KP prompt rewrite and player-experience constraints: Task 6.
- Streaming config: Task 7.
- Verification: Task 8.

Type consistency:

- Profile fields use `tool_names` and `context_providers` consistently.
- Tool handlers use `(arguments, context) -> dict`.
- Context uses `room_id`, `room_dir`, `scenarios_dir`, `user_id`, and `agent_id`.
- Runtime result uses `content`, `token_count`, `error`, and `response_data`.
