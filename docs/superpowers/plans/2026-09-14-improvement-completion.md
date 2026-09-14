# Improvement Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the remaining `docs/improvement.md` requirements without replacing existing room, scenario, or AI runtime modules.

**Architecture:** Keep JSON file storage and the current lexical knowledge-card index. Add version snapshots beside the canonical scenario record, route room reads through the pinned snapshot, expose explicit migration/archive operations, and use existing in-memory cache classes at the chat application layer.

**Tech Stack:** Python 3.11, Flask, pytest, TypeScript, existing JSON storage and frontend templates.

**Spec:** `docs/improvement.md`

## Global Constraints

- Preserve existing API compatibility and existing room/scenario file formats.
- Do not add vector database or embedding dependencies; document lexical retrieval as the default fallback.
- Every versioned cache key and knowledge-card filter must include `scenario_version`.
- Active room state must not be silently changed by scenario edits.

---

### Task 1: Version snapshots and room migration

**Files:**
- Modify: `backend/trpg_server/scenario_store.py`
- Modify: `backend/trpg_server/agents/versioning.py`
- Modify: `backend/trpg_server/routes/scenarios.py`
- Modify: `backend/trpg_server/routes/rooms.py`
- Test: `tests/test_versioning.py`

- [ ] Add snapshot path/read/write helpers and migration validation.
- [ ] Save every published scenario version under its scenario directory.
- [ ] Load a room's pinned version before falling back to the latest record.
- [ ] Add explicit migration endpoint with mapping validation and rollback-safe room update.
- [ ] Prevent deleting scenarios referenced by active rooms; mark archived instead.
- [ ] Test old-room isolation, migration mapping, archive behavior, and rollback-safe failure.

### Task 2: Cache layers in chat runtime

**Files:**
- Modify: `backend/trpg_server/routes/chat.py`
- Modify: `backend/trpg_server/agents/cache.py`
- Test: `tests/test_cache_layers.py`

- [ ] Add versioned exact-response keys containing scenario, version, scene, and state hash.
- [ ] Add room-scoped semantic keys containing room ID.
- [ ] Read/write exact and semantic caches around the completion request.
- [ ] Keep provider prefix cache independent of room ID and record all cache metrics.
- [ ] Test exact reuse, semantic room isolation, and version invalidation.

### Task 3: Strict structured output validation

**Files:**
- Modify: `backend/trpg_server/agents/structured_output.py`
- Modify: `backend/trpg_server/routes/chat.py`
- Test: `tests/test_structured_output.py`

- [ ] Add a canonical JSON schema constant for KP responses.
- [ ] Validate `npc_actions` NPC IDs and action shape against current scenario entities.
- [ ] Return rejection metadata for illegal state/entity updates without retrying the model.
- [ ] Record a validation event in room state when illegal output is discarded.

### Task 4: Frontend version display and documentation

**Files:**
- Modify: `frontend/src/types/scenario.d.ts`
- Modify: `frontend/src/app/views/ScenarioView.ts`
- Modify: `frontend/src/templates/scenario.html`
- Modify: `README.md`
- Test: `tests/test_frontend_project_structure.py`

- [ ] Add `scenario_version` to frontend scenario types and list/preview/edit displays.
- [ ] Document migration/archive endpoints, cache behavior, lexical retrieval tradeoff, and examples.
- [ ] Add an architecture diagram and measurable verification commands.

### Task 5: Full verification

- [ ] Run targeted tests for each task.
- [ ] Run `pytest -q`.
- [ ] Run `scripts/verify.ps1`.
- [ ] Run `git diff --check` and report remaining limitations explicitly.
