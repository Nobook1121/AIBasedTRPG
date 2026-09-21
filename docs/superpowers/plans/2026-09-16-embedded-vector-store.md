# Embedded Vector Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make embedded SQLite vector storage the default while preserving the optional Qdrant backend and existing knowledge retrieval behavior.

**Architecture:** A backend-neutral vector-store contract fronts an SQLite implementation and the existing Qdrant adapter. The app factory selects the backend from environment configuration; scenario indexing writes both the JSON backup and vector rows, while retrieval keeps current hard filters and score fusion.

**Tech Stack:** Python 3, Flask, SQLite stdlib, existing embedding providers, optional `qdrant-client`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-embedded-vector-store-design.md`

## Global Constraints

- Default startup must not require Docker, Qdrant, or any external service.
- Embedded data must be persisted under `data/runtime/vector-db/embedded/`.
- Existing JSON knowledge indexes remain at `data/scenarios/scenario-<id>/knowledge-index/<version>.json`.
- `AI_TRPG_VECTOR_BACKEND` accepts `embedded` or `qdrant` and defaults to `embedded`.
- A non-empty `AI_TRPG_VECTOR_DB_URL` remains compatible and selects Qdrant unless explicitly overridden.
- Existing hard filters and import progress stages must not regress.

---

### Task 1: Define the vector-store contract and embedded SQLite implementation

**Files:**
- Modify: `backend/trpg_server/agents/vector_store.py`
- Create: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: mappings with `chunk_id`/`id`, `embedding`/`vector`, and metadata fields.
- Produces: `VectorStore`, `EmbeddedVectorStore`, `QdrantVectorStore`, and `create_vector_store()`.

- [ ] **Step 1: Write failing contract tests** for embedded upsert/query/filter/delete/count/health and cosine ordering.
- [ ] **Step 2: Run `pytest -q tests/test_vector_store.py` and verify the new symbols fail to import or assertions fail for the missing behavior.**
- [ ] **Step 3: Implement SQLite schema, atomic batch upsert, metadata filter matching, cosine query, deletion, count, health, and backend-neutral result conversion.
- [ ] **Step 4: Run the focused tests and verify they pass.**
- [ ] **Step 5: Refactor only after green, retaining the existing Qdrant behavior through the same contract.**

### Task 2: Select the backend from configuration and initialize it at startup

**Files:**
- Modify: `backend/trpg_server/settings.py`
- Modify: `backend/trpg_server/app_factory.py`
- Create: `tests/test_vector_store_selection.py`

**Interfaces:**
- Consumes: `AI_TRPG_VECTOR_BACKEND`, `AI_TRPG_VECTOR_DB_URL`, and existing vector paths.
- Produces: `app.extensions["vector_store"]` containing the selected backend.

- [ ] **Step 1: Add failing tests** for default embedded selection, explicit Qdrant selection, and URL compatibility.
- [ ] **Step 2: Run the focused selection tests and observe failure before implementation.**
- [ ] **Step 3: Add settings/config wiring and call `create_vector_store()` from `create_app()`.**
- [ ] **Step 4: Run selection tests and the existing app-factory tests.**

### Task 3: Index chunks into the selected store without changing retrieval semantics

**Files:**
- Modify: `backend/trpg_server/agents/knowledge_base.py`
- Modify: `backend/trpg_server/scenario_import_pipeline.py`
- Modify: `backend/trpg_server/scenario_store.py`
- Create or modify: `tests/test_knowledge_base.py`, `tests/test_scenario_import_pipeline.py`

**Interfaces:**
- Consumes: `KnowledgeChunk`, `EmbeddingProvider`, and selected `VectorStore`.
- Produces: idempotent vector rows keyed by scenario/version/chunk while preserving JSON index writes and import progress names.

- [ ] **Step 1: Add failing tests** proving persisted scenario indexes are also upserted and repeated indexing does not duplicate rows.
- [ ] **Step 2: Run focused tests and verify the expected failures.**
- [ ] **Step 3: Add a small indexing helper that embeds missing chunk text, upserts chunks, and leaves JSON persistence intact.**
- [ ] **Step 4: Update import and scenario-save call sites to use the helper.**
- [ ] **Step 5: Run knowledge-base and import tests, then the complete Python suite.**

### Task 4: Add JSON-to-embedded migration and operational configuration

**Files:**
- Create: `scripts/migrate-vector-store.py`
- Modify: `config/vector-embedding-ocr.example.env`
- Modify: `requirements.txt`
- Create: `requirements-vector-qdrant.txt`
- Create: `tests/test_vector_migration.py`

**Interfaces:**
- Consumes: scenario JSON indexes and an embedded store path.
- Produces: idempotent migration command and split dependency files.

- [ ] **Step 1: Add failing migration tests** for importing a versioned JSON index twice with stable counts.
- [ ] **Step 2: Run the focused migration tests and verify failure.**
- [ ] **Step 3: Implement migration discovery and import with clear summary output and no destructive deletes.**
- [ ] **Step 4: Move Qdrant dependency to the optional requirements file and document the environment variables.**
- [ ] **Step 5: Run migration tests and dependency/config checks.**

### Task 5: Document defaults, optional Qdrant, data paths, and validation

**Files:**
- Modify: `README.md`
- Modify: `docs/development.md`
- Modify: `docs/improvement.md` only if an implementation checklist is needed

- [ ] **Step 1: Document zero-external-dependency startup, backend selection, migration, storage paths, and scale limits.**
- [ ] **Step 2: Run `pytest -q`, `npm run typecheck`, `npm run build:frontend`, `scripts/verify.ps1`, and `git diff --check`.**
- [ ] **Step 3: Re-read the plan and report any uncovered requirement before claiming completion.**

