# Scenario Import Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a persistent asynchronous workflow that converts Word, PDF, TXT, and Markdown files into reviewable versioned scenario cards and a room-safe knowledge index.

**Architecture:** Keep the existing Flask app, JSON scenario store, module editor, room version binding, and `KnowledgeBaseService`. Add focused document, pipeline, job-store, and route modules; stream persisted job snapshots to the frontend; publish reviewed cards through the existing scenario store so version snapshots and knowledge indexes remain authoritative.

**Tech Stack:** Python 3.11, Flask 2.3, `ThreadPoolExecutor`, PyMuPDF, JSON atomic storage, pytest, TypeScript 5.8, existing Bootstrap/template frontend.

**Spec:** `docs/superpowers/specs/2026-09-15-scenario-import-pipeline-design.md`

## Global Constraints

- Preserve `/api/scenarios/import` as the synchronous compatibility endpoint.
- Store jobs under `data/runtime/scenario_imports/<job_id>/` and published scenarios under `data/scenarios/scenario-<id>/`.
- Keep room bindings immutable across publication; only explicit migration may change a room version.
- Filter scenario, version, scene, spoiler, visibility, and unlock state before scoring.
- Do not add Celery, Redis, Chroma, Milvus, OCR, or a reranker.
- Use PyMuPDF for text PDF extraction; scanned PDFs return a clear retryable parsing error.
- Preserve the original upload and every completed intermediate stage.
- Use existing permissions `scenarios.create` and `scenarios.edit`.

---

## File Structure

- Create `backend/trpg_server/scenario_documents.py` for format validation, PDF/DOCX extraction, and chunking.
- Create `backend/trpg_server/scenario_import_pipeline.py` for local extraction, merge, card, summary, and embedding stages.
- Create `backend/trpg_server/scenario_import_jobs.py` for persisted job state, cancellation, retry, and executor lifecycle.
- Create `backend/trpg_server/routes/scenario_imports.py` for upload, status, SSE, retry, cancel, preview, publish, versions, search, and reindex APIs.
- Modify `backend/trpg_server/agents/knowledge_base.py` for source metadata, embeddings, unlock filtering, and fused scoring.
- Modify `backend/trpg_server/scenario_store.py`, `app_factory.py`, and `settings.py` for source manifests, version listing, directories, limits, and blueprint registration.
- Modify `frontend/src/types/scenario.d.ts`, `ScenarioModel.ts`, `ScenarioController.ts`, `ScenarioView.ts`, `02-main-tabs.html`, `scenario.html`, and `02-scenario-character.css` for upload, progress, review, and publish.
- Modify `README.md`, `docs/api.md`, and `docs/scenario-import.md`; create `scripts/reindex-scenarios.py`.

### Task 1: Structured document parsing and chunking

**Files:** Create `backend/trpg_server/scenario_documents.py`; modify `backend/trpg_server/scenario_importer.py` and `requirements.txt`; create `tests/test_scenario_documents.py`.

**Interfaces:** `validate_scenario_upload(filename, size, max_bytes) -> str`, `parse_scenario_document(raw, filename) -> ParsedDocument`, and `chunk_parsed_document(document, target_min=800, target_max=1500, overlap=150) -> list[DocumentChunk]`.

- [ ] Write failing tests for Markdown heading paths, exact overlap, PDF page references, DOCX tables, unsupported formats, and scanned-PDF OCR errors.
- [ ] Run `pytest tests/test_scenario_documents.py -q`; expect missing-module collection failure.
- [ ] Add `PyMuPDF>=1.24,<2` and implement `DocumentBlock`, `ParsedDocument`, and `DocumentChunk` dataclasses.
- [ ] Use `fitz.open(stream=raw, filetype="pdf")`, preserve page numbers and span font sizes, infer headings, and reject pages with no meaningful text using `ScenarioDocumentError("PDF appears scanned; OCR is required")`.
- [ ] Extend DOCX extraction to include headings, lists, and table cells; keep `extract_script_text` delegating to this parser so the synchronous endpoint also supports PDF.
- [ ] Implement heading-first chunking; heading-less text aggregates paragraphs to 800–1500 Unicode characters, splits before 1500, and prefixes exactly 150 overlap characters.
- [ ] Run `pytest tests/test_scenario_documents.py tests/test_scenario_modules.py -q`; expect all pass.
- [ ] Commit with `git add requirements.txt backend/trpg_server/scenario_documents.py backend/trpg_server/scenario_importer.py tests/test_scenario_documents.py; git commit -m "feat: parse and chunk scenario documents"`.

### Task 2: Persistent jobs and resumable pipeline

**Files:** Create `backend/trpg_server/scenario_import_jobs.py` and `backend/trpg_server/scenario_import_pipeline.py`; modify `settings.py` and `app_factory.py`; create `tests/test_scenario_import_jobs.py`.

**Interfaces:** `ImportJobStore.create/get/update/save_intermediate/load_intermediate/request_cancel/recover_interrupted`; `ScenarioImportPipeline.run(job_id, start_stage=None)`; `submit_import_job(app, job_id, start_stage=None)`.

- [ ] Write failing tests for atomic state persistence across store instances, cancellation at a stage boundary, recovery of interrupted jobs, successful intermediate files, and retry dependency validation.
- [ ] Run `pytest tests/test_scenario_import_jobs.py -q`; expect missing-module failure.
- [ ] Implement `IMPORT_STAGES = ("parsing", "chunking", "extracting", "merging", "carding", "summarizing", "embedding")`, an `RLock`, token-safe job IDs, millisecond script IDs, atomic `job.json`, and relative intermediate paths.
- [ ] Implement stage dependency checks so retry can start only where prerequisite intermediate JSON exists; preserve successful outputs on failure.
- [ ] Implement deterministic local extraction from existing section boundaries, source references, module metadata, global summary, and per-card warnings. Check cancellation before every stage and chunk.
- [ ] Add `SCENARIO_IMPORTS_DIR`, `SCENARIO_IMPORT_MAX_BYTES=32*1024*1024`, and `SCENARIO_IMPORT_WORKERS=2`; create one executor/store in `app.extensions`, recover interrupted jobs at startup, and execute workers inside `app.app_context()`.
- [ ] Run `pytest tests/test_scenario_import_jobs.py -q`; expect all pass.
- [ ] Commit with `git add backend/trpg_server/settings.py backend/trpg_server/app_factory.py backend/trpg_server/scenario_import_jobs.py backend/trpg_server/scenario_import_pipeline.py tests/test_scenario_import_jobs.py; git commit -m "feat: persist resumable scenario import jobs"`.

### Task 3: Knowledge cards, embeddings, summaries, and retrieval

**Files:** Modify `scenario_import_pipeline.py`, `backend/trpg_server/agents/knowledge_base.py`, and `backend/trpg_server/agents/prompt_builder.py`; create `tests/test_scenario_import_pipeline.py`; extend existing knowledge/prompt tests.

**Interfaces:** `EmbeddingProvider.embed(texts)`, `HashedTokenEmbedding`, extended `KnowledgeChunk`, `build_import_preview(job)`, and fused `KnowledgeBaseService.search` results containing `source_ref` and `score_components`.

- [ ] Write failing tests proving cards retain `source_ref.quote/chunk_id`, conflicts, embeddings, and that locked or wrong-version cards are removed before scoring.
- [ ] Run focused tests and confirm new assertions fail.
- [ ] Extend `KnowledgeChunk` with optional `source_ref` and `metadata`; load old index records with missing fields instead of dropping them.
- [ ] Implement normalized hashed character-bigram/token vectors and an optional OpenAI-compatible embedding adapter; on provider failure persist fallback vectors and warnings.
- [ ] Apply hard filters for scenario/version/scene/spoiler/audience/unlocked IDs before computing scores; fuse normalized lexical and cosine scores with deterministic chunk-ID tie ordering.
- [ ] Generate a 500–1000 character global summary, save it as `global_summary` and a `core` card, and update prompt construction to inject the core summary, current-scene summaries, and top five cards only.
- [ ] Run `pytest tests/test_scenario_import_pipeline.py tests/test_knowledge_base.py tests/test_prompt_builder.py -q`; expect all pass.
- [ ] Commit with `git add backend/trpg_server/scenario_import_pipeline.py backend/trpg_server/agents/knowledge_base.py backend/trpg_server/agents/prompt_builder.py tests/test_scenario_import_pipeline.py tests/test_knowledge_base.py tests/test_prompt_builder.py; git commit -m "feat: enrich scenario knowledge retrieval"`.

### Task 4: Import and publication APIs

**Files:** Create `backend/trpg_server/routes/scenario_imports.py`; modify `app_factory.py` and `scenario_store.py`; create `tests/test_scenario_import_routes.py`.

**Interfaces:** `POST /api/scripts/import`, `GET /api/scripts/import/<job_id>`, `GET /api/scripts/import/<job_id>/stream`, `POST .../retry`, `POST .../cancel`, `PUT .../preview`, `POST /api/scripts/<id>/publish`, `GET /api/scripts/<id>/versions`, `POST /api/scripts/<id>/search`, and `POST /api/scripts/<id>/reindex`.

- [ ] Write failing authenticated tests for multipart upload returning `202`, ownership isolation returning `404`, SSE snapshots, retry/cancel, preview persistence, publish creating `scenario.json`, `versions/<n>.json`, `knowledge-index/<n>.json`, and room immutability.
- [ ] Run `pytest tests/test_scenario_import_routes.py -q`; expect 404s.
- [ ] Implement login/permission/ownership helpers; sanitize filename and write source inside the job directory before submission.
- [ ] Implement status payloads that omit embedding arrays. SSE emits an immediate snapshot, changed snapshots, 15-second heartbeats, terminal completion, `Cache-Control: no-cache`, and `X-Accel-Buffering: no`.
- [ ] Implement retry dependency validation, cancellation, normalized preview saves, and publish with source copy plus `imports/<job_id>/manifest.json`; mark published only after all atomic writes succeed.
- [ ] Add `list_scenario_versions(descriptor_path)` and protected version/search/reindex endpoints.
- [ ] Run `pytest tests/test_scenario_import_routes.py tests/test_versioning.py tests/test_scenario_modules.py -q`; expect all pass.
- [ ] Commit with `git add backend/trpg_server/routes/scenario_imports.py backend/trpg_server/app_factory.py backend/trpg_server/scenario_store.py tests/test_scenario_import_routes.py; git commit -m "feat: expose scenario import workflow api"`.

### Task 5: Frontend upload and progress restoration

**Files:** Modify frontend scenario types/model/controller/view/fragment/template/styles; extend `tests/test_frontend_project_structure.py`.

**Interfaces:** `ScenarioImportJob`, `createImportJob`, `getImportJob`, `retryImportJob`, `cancelImportJob`, `saveImportPreview`, and `publishImportJob`.

- [ ] Write failing structural tests for a drag/drop zone, `.docx,.pdf,.txt,.md` accept list, `sessionStorage` key `ai-trpg:scenario-import-job`, `EventSource`, and `pollImportJob`.
- [ ] Run the focused test and confirm assertion failure.
- [ ] Add exact job/status/source-reference/conflict TypeScript types and model methods; use `XMLHttpRequest` only for upload progress and `TrpgApi` otherwise.
- [ ] Add Bootstrap upload modal with title/author/description/public fields, extension and 32 MiB checks, drag/drop, selected filename, and submit state.
- [ ] Store only job ID in `sessionStorage`; restore on controller init, display eight backend stages, reconnect SSE, and poll every two seconds after SSE errors. Never display a percentage above the latest server value.
- [ ] Add cancel confirmation and failed-stage retry; keep job visible until terminal server state.
- [ ] Run `pytest tests/test_frontend_project_structure.py -q` and `npm run typecheck`; expect pass.
- [ ] Commit with `git add frontend/src tests/test_frontend_project_structure.py; git commit -m "feat: show persistent scenario import progress"`.

### Task 6: Review provenance and publish UI

**Files:** Modify `ScenarioController.ts`, `ScenarioView.ts`, `scenario.html`, types, and scenario styles; extend frontend structure tests.

- [ ] Write failing tests for `source_ref`, `metadata.conflicts`, card type/spoiler/search filters, and `confirmScenarioImportPublish`.
- [ ] Run the focused test and confirm failure.
- [ ] Enter review mode with `job.preview`, make the global summary editable, change primary action to publish, and autosave via the import preview endpoint.
- [ ] Render source page/chapter/chunk/quote in a collapsible panel; mark conflict cards with accessible warning text; keep filters from deleting underlying form data.
- [ ] Require a second publish confirmation, clear session state after success, reload scenario list, and show the published preview.
- [ ] Run `pytest tests/test_frontend_project_structure.py -q`, `npm run typecheck`, and `npm run build:frontend`; expect pass.
- [ ] Commit with `git add frontend/src tests/test_frontend_project_structure.py; git commit -m "feat: review and publish imported scenario cards"`.

### Task 7: Reindex existing data and documentation

**Files:** Create `scripts/reindex-scenarios.py` and `tests/test_scenario_reindex.py`; modify `README.md`, `docs/api.md`, and `docs/scenario-import.md`.

- [ ] Write an idempotence test proving missing indexes are rebuilt without changing `scenario.json`, versions, rooms, or source files.
- [ ] Run the test and confirm the script is missing.
- [ ] Implement `reindex_scenarios(scenarios_dir) -> dict[str, int]`; enumerate descriptors and every `versions/*.json`, write only corresponding `knowledge-index/<version>.json`, and report written/skipped/failed counts.
- [ ] Document exact paths: `data/scenarios/scenario-<id>/scenario.json`, `versions/<version>.json`, `knowledge-index/<version>.json`, `source/`, `imports/`, and `data/runtime/scenario_imports/<job_id>/`; document PyMuPDF, APIs, SSE fallback, retry, room isolation, OCR limitation, and backup requirements.
- [ ] Run `pytest tests/test_scenario_reindex.py tests/test_backend_project_structure.py tests/test_frontend_project_structure.py -q`.
- [ ] Run `python scripts/reindex-scenarios.py` to create missing indexes for readable existing versions.
- [ ] Commit with `git add scripts/reindex-scenarios.py tests/test_scenario_reindex.py README.md docs/api.md docs/scenario-import.md; git commit -m "docs: explain scenario import and index storage"`.

### Task 8: Full verification

- [ ] Run focused suites for documents, jobs, pipeline, routes, reindex, knowledge, and versioning.
- [ ] Run `pytest -q`.
- [ ] Run `npm run typecheck` and `npm run build:frontend`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1` and `git diff --check`.
- [ ] Inspect actual output with `Get-ChildItem data/scenarios -Recurse -File` and `Get-ChildItem data/runtime/scenario_imports -Recurse -File`; report formal scenarios, version snapshots, indexes, source documents, manifests, and intermediates separately.
- [ ] Commit only verification fixes if needed; otherwise do not create an empty commit.
