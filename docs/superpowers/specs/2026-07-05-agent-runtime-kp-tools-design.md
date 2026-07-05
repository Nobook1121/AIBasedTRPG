# Agent Runtime and KP Tools Design

## Scope

This change adds a modular AI agent runtime for room-aware TRPG assistants. KP is the first supported agent profile, but the design must allow future agents to use different prompts, context providers, and function/tool sets without rewriting the chat route.

The first KP implementation must:

- Load the current room scenario, relevant scene data, room character cards, character background, and room memory into the AI context when needed.
- Let the model request tools/functions through an OpenAI-compatible tool-calling loop.
- Execute COC7 dice checks through backend tool code, not through model-generated dice results.
- Persist and retrieve room memory.
- Add a configurable AI streaming flag.
- Replace the broken `data/config/roles/kp.md` content with valid UTF-8 Chinese prompt text.

## Existing Context

Current `/api/chat` directly builds a single request payload from role prompt, recent user-level history, and user content. It stores recent chat history under `HISTORY_DIR` by `user_id`.

Rooms already contain:

- `info.json`: room metadata, `scenario_id`, members, bound character card snapshots, HP/SAN state.
- `messages.json`: visible room messages.
- `nodes/*.json` and `autosave.json`: room archive data.

Scenarios are JSON files under `SCENARIOS_DIR`, loaded by `trpg_server.routes.scenarios`.

The existing dice tool is frontend-only. A backend dice implementation is required for model tool calls.

## Recommended Architecture

Add a backend agent runtime layer under `trpg_server/agents/`.

Core modules:

- `runtime.py`: generic OpenAI-compatible tool loop.
- `profiles.py`: loads role/agent profile data, prompt, provider, and declared tool names.
- `context.py`: builds generic request context from user, room, scenario, and role inputs.
- `tools/base.py`: small registry and tool result contract.
- `tools/room.py`: room/scenario/character/memory tools.
- `tools/dice.py`: dice parsing and COC7 check execution.
- `memory.py`: room-scoped memory persistence.
- `config.py`: AI runtime configuration such as streaming.

KP-specific behavior belongs in:

- `data/config/roles/kp.md`: prompt and behavior policy.
- a KP profile entry in role config, using the generic runtime and enabling KP tools.

Future agents should be added by registering:

- prompt file or prompt text,
- wake words,
- provider,
- enabled tool names,
- optional context provider names.

The chat route should not contain KP-specific tool logic. It should resolve the requested role/agent profile and hand off to the runtime.

## Agent Profile Contract

Each agent profile should resolve to:

```json
{
  "id": "kp",
  "name": "KP",
  "prompt": "...",
  "provider": "openrouter",
  "wake_words": ["@KP"],
  "tools": [
    "room.get_scenario_context",
    "room.get_character_cards",
    "room.get_memory",
    "room.remember_fact",
    "dice.roll_coc_check"
  ],
  "context": ["room.recent_messages"]
}
```

If older role config files do not contain `tools` or `context`, KP should receive the default KP tool set. Other profiles should default to no tools unless configured.

## Tool Calling Flow

`/api/chat` should:

1. Validate input and resolve `role_id`, `room_id`, `user_id`, and content.
2. Load the selected agent profile.
3. Load the enabled AI platform and model.
4. Build the base message list:
   - system prompt,
   - compact room/session context if available,
   - recent room messages or fallback user history,
   - current user message.
5. Attach tool schemas from the selected profile.
6. Send the model request.
7. If the response contains tool calls:
   - validate tool name against profile permissions,
   - execute the backend tool,
   - append tool results to messages,
   - call the model again.
8. Stop after a bounded number of tool rounds.
9. Persist final assistant response and recent history.

The runtime must handle both `tool_calls` and legacy `function_call` shapes where practical, because OpenAI-compatible providers vary.

## KP Tools

### `room.get_scenario_context`

Input:

```json
{
  "query": "optional scene or clue search text",
  "scene_id": "optional explicit scene id",
  "max_items": 5
}
```

Output should include scenario title, description, matching scenes, NPCs, clues, locations, or raw fallback sections if the scenario schema is not fully known.

The tool must not expose file paths or unrelated scenarios. It only uses the current room's `scenario_id`.

### `room.get_character_cards`

Input:

```json
{
  "include_inactive": false
}
```

Output includes active room members, player names, bound character cards, attributes, skills, background, equipment, HP/SAN state, and notable status records.

### `dice.roll_coc_check`

Input:

```json
{
  "character_name": "optional",
  "skill": "Locksmith",
  "target": 45,
  "difficulty": "regular",
  "bonus_dice": 0,
  "penalty_dice": 0,
  "reason": "open the cellar door"
}
```

Behavior:

- Roll real `1d100` in backend code.
- Support regular, hard, and extreme target thresholds.
- Support bonus/penalty dice for COC7 percentile checks.
- Return raw roll details, target, threshold, success level, fumble/critical flags, and a concise Chinese result summary.
- Never accept a caller-supplied final roll value in production requests.

### `room.remember_fact`

Input:

```json
{
  "kind": "npc_state",
  "content": "The librarian now distrusts the investigators.",
  "importance": 3
}
```

Behavior:

- Persist room-scoped memory in a JSON file under the room directory, for example `agent_memory.json`.
- Store timestamp, agent id, authoring user/request metadata when available, kind, content, and importance.
- Bound item size and total memory count to avoid unbounded context growth.

### `room.get_memory`

Input:

```json
{
  "query": "optional",
  "limit": 10
}
```

Behavior:

- Return recent and important memory items for the current room.
- Start with simple keyword/recent filtering. Do not add vector dependencies in this change.

## KP Prompt Requirements

Rewrite `data/config/roles/kp.md` as valid UTF-8 Chinese. The prompt must state:

- You are a COC7 Keeper.
- Use tools when scenario, room, character, memory, or dice data is needed.
- Do not invent dice rolls or check results.
- Ask for or trigger a dice check only when rules or meaningful uncertainty require it.
- Every player should have meaningful spotlight time.
- Do not kill investigators without clear rule-backed and fiction-backed cause.
- Do not remove agency from players.
- Failed checks should usually be framed as world resistance, environmental complication, time pressure, damaged tools, unreliable evidence, or external interference instead of player incompetence.
- Failed checks should still move the story forward where possible.
- Strictly follow COC7 rules for checks, difficulty, sanity loss, combat, chase, wounds, and consequences.

## Memory Semantics

There are three memory layers:

1. Recent visible room messages: short-term conversational continuity.
2. Room agent memory: explicit facts the agent records for future consistency.
3. Scenario and character source data: canonical game state.

Canonical room/scenario/character data wins over memory if they conflict. The KP prompt should instruct the model to treat memory as session continuity, not immutable truth.

## Streaming Configuration

Add to `data/config/general.toml`:

```toml
[ai]
stream_output = false
```

Expose it in the settings UI as a checkbox in chat/model settings.

Backend behavior:

- Read `ai.stream_output`.
- Include `"stream": true` only when the setting is enabled and the current route supports it.
- If the provider returns streaming but the frontend endpoint is still non-streaming, the backend may aggregate chunks into a complete response before returning.

This keeps the setting available without forcing a frontend streaming rewrite in the same change.

## Error Handling

- Missing room: continue as non-room chat only if `room_id` is absent; otherwise return permission or not found errors.
- Missing scenario: add a system context note and continue with room/character context.
- Missing character card: return that fact in `get_character_cards`, not as a hard error.
- Unknown or unauthorized tool: return a controlled tool error to the model and log it.
- Tool loop limit exceeded: return an error response rather than an infinite loop.
- Invalid dice target/difficulty: return a tool validation error.
- Provider tool incompatibility: degrade to prompt-only request with a system note only if no tool call was requested; do not fabricate tool results.

## Tests

Add focused pytest coverage for:

- KP prompt file is valid UTF-8 and contains no mojibake fallback text.
- Profile resolution gives KP the default tool set when role config lacks explicit tools.
- Agent runtime executes a tool call and sends the tool result back to the model.
- Runtime rejects unauthorized tools.
- Room scenario context tool only loads the current room's scenario.
- Character card tool returns active room members and bound card background/state.
- COC7 check tool rolls backend dice and calculates success levels.
- Room memory can be written and read back.
- AI stream config is read from `general.toml`.
- Settings UI and frontend config code include `stream_output`.

## Non-Goals

- Full SSE/WebSocket streaming renderer.
- Vector search or embeddings for memory.
- Automatic HP/SAN mutation from all KP narration.
- Replacing frontend manual dice commands.
- Complete COC7 combat/chase automation beyond percentile checks in this change.

## Migration Notes

- Existing chat API response shape should remain compatible: `content`, `token_count`, and error fields.
- Existing room messages should remain unchanged.
- Existing frontend dice tool remains available for manual `/dice`.
- New backend dice tools are authoritative for AI function calls.
- Existing role configs without tool declarations should continue to load.
