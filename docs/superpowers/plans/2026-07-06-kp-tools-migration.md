# KP Tools Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make KP context compact, route checks through the check tool first, reserve dice rolls as fallback, and centralize frontend small-tool source under `tools`.

**Architecture:** Backend room tools return natural-language compact summaries for agent context while keeping full character cards available only inside check execution. Frontend tool source moves from `frontend/src/tools` to root `tools`, with the build script changed so generated JavaScript is copied to `data/tools` without deleting TypeScript source.

**Tech Stack:** Python Flask backend, pytest, TypeScript frontend, PowerShell verification script.

---

### Task 1: Backend Context Summaries

**Files:**
- Modify: `trpg_server/agents/tools/room.py`
- Modify: `trpg_server/routes/chat.py`
- Test: `tests/test_agent_tools.py`
- Test: `tests/test_chat_agent_context.py`

- [ ] Add failing pytest coverage that `room.get_room_snapshot` and the automatic chat system message do not include raw `attributes`, `skills`, HP/MP/SAN, or full scenario JSON.
- [ ] Implement compact scenario and character natural-language summaries in `trpg_server/agents/tools/room.py`.
- [ ] Change `trpg_server/routes/chat.py` to inject the compact text instead of `_json_for_log(snapshot)`.
- [ ] Run the focused pytest files.

### Task 2: Check-First Tool Policy

**Files:**
- Modify: `data/config/roles/kp.md`
- Modify: `trpg_server/agents/tools/dice.py`
- Test: `tests/test_agent_tools.py`
- Test: `tests/test_kp_prompt_and_stream_config.py`

- [ ] Add failing tests that the KP prompt explicitly requires `check.roll_room_check` first and treats `dice.roll_coc_check` as fallback only.
- [ ] Make tool descriptions match that policy.
- [ ] Ensure `check.roll_room_check` still reads full bound character cards internally even though card summaries are compact.
- [ ] Run the focused pytest files.

### Task 3: Frontend Small-Tool Source Migration

**Files:**
- Move: `frontend/src/tools/diceTool.ts` to `tools/diceTool.ts`
- Move: `frontend/src/tools/toolManager.ts` to `tools/toolManager.ts`
- Modify: `tsconfig.json`
- Modify: `tsconfig.frontend.json`
- Modify: `scripts/relocate-tools.mjs`
- Modify: `scripts/verify.ps1`
- Test: `tests/test_frontend_build_structure.py`

- [ ] Add failing tests that frontend tool source lives under root `tools` and not under `frontend/src/tools`.
- [ ] Move TypeScript source files to root `tools`.
- [ ] Update TypeScript configs to include root `tools/**/*.ts`.
- [ ] Change `scripts/relocate-tools.mjs` to copy generated `.js` files from `tools` to `data/tools` and remove only generated `.js`, not the source directory.
- [ ] Run `npm run typecheck` and `npm run build:frontend`.

### Task 4: Verification

**Files:**
- Run: `scripts/verify.ps1`

- [ ] Run the full verification script.
- [ ] Review `git diff --check`.
- [ ] Report exact verification results and any remaining risks.
