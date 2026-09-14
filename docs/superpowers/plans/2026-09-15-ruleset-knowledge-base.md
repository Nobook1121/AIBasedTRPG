# Ruleset Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an extensible, administrator-managed external ruleset knowledge base beginning with COC7, with semantic chunking distinct from scenario chunks and room-aware retrieval.

**Architecture:** Introduce a ruleset adapter/registry layer and versioned JSON indexes under `data/runtime/knowledge-bases`. Keep ruleset and scenario namespaces separate, bind active versions to rooms, and inject retrieved rules into the layered prompt as reference-only context. Expose guarded admin APIs and a settings UI, while preserving old active versions on failed indexing.

**Tech Stack:** Python/Flask, existing JSON persistence and text extraction, pytest, TypeScript frontend.

**Spec:** `docs/superpowers/specs/2026-09-14-ruleset-knowledge-base-design.md`

## Global Constraints

- Ruleset chunks must be semantically grouped by headings, topics, formulas, tables, exceptions, and examples; never reuse scenario scene/module chunking.
- Ruleset and scenario data use separate namespaces and indexes.
- Upload, reindex, enable, archive, and room-binding mutations require `settings.knowledge_bases`.
- Failed indexing must leave the previous active version usable; archive must be recoverable metadata, not destructive deletion.
- External rule text is reference material only and must never become executable system instructions.
- New storage and API behavior must remain backward-compatible when no ruleset is bound.

---

### Task 1: Ruleset chunk model and adapters

**Files:**
- Create: `backend/trpg_server/agents/ruleset_adapters.py`
- Create: `backend/trpg_server/agents/ruleset_knowledge.py`
- Test: `backend/tests/test_ruleset_knowledge.py`

**Interfaces:**
- Produces `RulesetChunk`, `RulesetAdapter`, `COC7Adapter`, `RulesetRegistry`, and deterministic semantic chunking used by storage and retrieval tasks.

- [ ] **Step 1: Write failing tests** for COC7 headings, formulas, table rows, exception text, adapter registration, and scenario/ruleset namespace isolation.
- [ ] **Step 2: Run** `pytest backend/tests/test_ruleset_knowledge.py -q` and confirm collection or assertion failures.
- [ ] **Step 3: Implement** immutable chunk metadata, safe text extraction reuse, COC7 topic classification, and heading-aware chunking that keeps formula/table/exception/example blocks together.
- [ ] **Step 4: Run** the focused tests and confirm they pass.
- [ ] **Step 5: Commit** with `git add backend/trpg_server/agents/ruleset_adapters.py backend/trpg_server/agents/ruleset_knowledge.py backend/tests/test_ruleset_knowledge.py && git commit -m "feat: add extensible ruleset adapters"`.

### Task 2: Versioned ruleset registry and retrieval

**Files:**
- Modify: `backend/trpg_server/agents/ruleset_knowledge.py`
- Test: `backend/tests/test_ruleset_knowledge.py`

**Interfaces:**
- Produces `RulesetKnowledgeStore.upload_source()`, `.reindex()`, `.search()`, `.list_sources()`, `.enable()`, `.archive()`, and room binding helpers returning JSON-safe records.

- [ ] **Step 1: Add failing tests** for version creation, active-version switching, failed-index preservation, multi-ruleset loading, deterministic search ranking, and old room bindings.
- [ ] **Step 2: Run** the focused tests and verify failures.
- [ ] **Step 3: Implement** `rulesets.json`, per-ruleset source/version/index/manifest persistence, atomic temp-file replacement, SHA-256 source metadata, and exact token matching with topic/locale filters.
- [ ] **Step 4: Run** focused tests and verify all pass.
- [ ] **Step 5: Commit** with `git add backend/trpg_server/agents/ruleset_knowledge.py backend/tests/test_ruleset_knowledge.py && git commit -m "feat: persist and search versioned rulesets"`.

### Task 3: Admin APIs and permissions

**Files:**
- Create: `backend/trpg_server/routes/knowledge_bases.py`
- Modify: `backend/trpg_server/permission_config.py`
- Modify: `backend/trpg_server/app_factory.py`
- Test: `backend/tests/test_ruleset_knowledge_routes.py`

**Interfaces:**
- Produces JSON endpoints for list/sources/upload/reindex/enable/archive and room ruleset binding; ordinary users receive 403.

- [ ] **Step 1: Write failing Flask client tests** covering admin success, non-admin denial, invalid extension/size, failed reindex retention, and explicit room binding.
- [ ] **Step 2: Run** `pytest backend/tests/test_ruleset_knowledge_routes.py -q` and confirm failures.
- [ ] **Step 3: Add `settings.knowledge_bases` to the settings permission group, register the blueprint, validate filenames/extensions and safe paths, and map requests to the store.
- [ ] **Step 4: Run route tests and confirm pass.
- [ ] **Step 5: Commit** with `git add backend/trpg_server/routes/knowledge_bases.py backend/trpg_server/permission_config.py backend/trpg_server/app_factory.py backend/tests/test_ruleset_knowledge_routes.py && git commit -m "feat: add protected ruleset knowledge APIs"`.

### Task 4: Room retrieval, prompt composition, and telemetry

**Files:**
- Modify: `backend/trpg_server/routes/chat.py`
- Modify: `backend/trpg_server/agents/prompt_builder.py`
- Modify: `backend/trpg_server/agents/telemetry.py`
- Test: `backend/tests/test_ruleset_prompt_telemetry.py`

**Interfaces:**
- Produces room-aware ruleset bindings, `search_ruleset(room_id, query, top_k=3)`, reference-only prompt sections, and telemetry fields `ruleset_ids`, `knowledge_versions`, `retrieval_topics`, `retrieval_chunk_count`, `retrieval_latency_ms`, `retrieval_citations`.

- [ ] **Step 1: Write failing tests** for prompt ordering, no room/state leakage into cached fixed summaries, retrieval namespace isolation, and telemetry aggregation.
- [ ] **Step 2: Run focused tests and verify failures.
- [ ] **Step 3: Implement binding lookup, retrieval timing/citations, prompt insertion after scene context and before scenario retrieval, and daily report aggregation.
- [ ] **Step 4: Run focused tests and then the existing chat/telemetry tests.
- [ ] **Step 5: Commit** with `git add backend/trpg_server/routes/chat.py backend/trpg_server/agents/prompt_builder.py backend/trpg_server/agents/telemetry.py backend/tests/test_ruleset_prompt_telemetry.py && git commit -m "feat: inject ruleset retrieval into AI prompts"`.

### Task 5: Administrator settings UI

**Files:**
- Modify: `frontend/src/app/tabs.ts`
- Modify: `frontend/src/index/fragments/03-room-tools-auth-settings.html`
- Modify: `frontend/src/locales/*.json` (only existing locale files)
- Test: existing frontend typecheck/build commands

**Interfaces:**
- Produces a settings tab that lists rulesets, upload/reindex/enable/archive actions, active version/source/chunk counts, and a ruleset preview without exposing mutation controls to unauthorized users.

- [ ] **Step 1: Add UI test or compile guard for the new DOM ids/API calls.
- [ ] **Step 2: Run the frontend check and confirm the new references fail until implemented.
- [ ] **Step 3: Add accessible controls, progress/error states, and localized labels while preserving existing settings tabs.
- [ ] **Step 4: Run TypeScript check and production build.
- [ ] **Step 5: Commit** with `git add frontend && git commit -m "feat: manage ruleset knowledge from settings"`.

### Task 6: Documentation and full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/improvement.md` only for completed checklist status if needed
- Test: repository verification scripts

- [ ] **Step 1: Document COC7 upload format, semantic chunking differences, permissions, room binding, telemetry fields, and adding future COC6/D&D adapters.
- [ ] **Step 2: Run `pytest -q`, `scripts/verify.ps1`, frontend typecheck/build, and `git diff --check`.
- [ ] **Step 3: Fix regressions surfaced by verification and rerun the failing command.
- [ ] **Step 4: Commit documentation and verification updates with `docs: document ruleset knowledge operations`.

## Self-review

- Adapter extensibility, COC7 semantic chunking, isolated namespaces, version retention, admin permissions, room binding, prompt ordering, telemetry, UI, and future ruleset onboarding each have an explicit task.
- Every task names concrete files, tests, interfaces, commands, and commit boundaries; no placeholder steps are used.
