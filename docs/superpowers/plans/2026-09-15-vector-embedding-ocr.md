# Local Vector, Embedding, and OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional local Qdrant retrieval, configurable OpenAI-compatible embeddings, and PaddleOCR fallback for scanned PDFs without breaking JSON/lexical fallback.

**Architecture:** Introduce provider facades (`VectorStore`, `EmbeddingProvider`, `OcrProvider`) so the import pipeline and `KnowledgeBaseService` remain backend-agnostic. Qdrant, remote embeddings, and PaddleOCR are opt-in through environment/config; failures preserve JSON indexes and mark warnings.

**Tech Stack:** Python 3.11, `qdrant-client`, `openai`, `paddleocr`, `paddlepaddle`, PyMuPDF, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-15-scenario-import-pipeline-design.md`

## Global Constraints

- Default startup must work without Docker, API keys, or OCR models.
- Qdrant data is persisted under `data/runtime/vector-db/qdrant/` via Docker volume mount.
- Never send full source documents to embedding/OCR providers; process chunks/pages only.
- Keep JSON knowledge indexes as durable fallback and migration source.
- Preserve room/version/spoiler/visibility filters before vector scoring.

### Task 1: Provider facades and configuration

**Files:** Create `backend/trpg_server/agents/vector_store.py`, `embedding_provider.py`, `ocr_provider.py`; modify `settings.py`, `requirements.txt`; create `docker-compose.qdrant.yml`; add provider tests.

- [ ] Add failing tests for hashed fallback, disabled Qdrant fallback, embedding dimension mismatch, OCR unavailable behavior, and environment parsing.
- [ ] Implement `QdrantVectorStore` with collection name `scenario_<script_id>_<version>`, payload indexes, upsert/search/delete, health check, and `fallback=None` behavior when unavailable.
- [ ] Implement `OpenAICompatibleEmbeddingProvider` using configured base URL/key/model with batch size, timeout, dimension validation, and deterministic `HashedTokenEmbedding` fallback.
- [ ] Implement `PaddleOcrProvider` lazy-loading `PaddleOCR(lang="ch")`, returning text, page, confidence; raise a clear install/model error when unavailable.
- [ ] Add config keys `VECTOR_DB_URL`, `VECTOR_DB_API_KEY`, `VECTOR_DB_PATH`, `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `OCR_ENABLED`, `OCR_LANG`.
- [ ] Add Compose service `qdrant/qdrant` with port `6333` and volume `./data/runtime/vector-db/qdrant:/qdrant/storage`.

### Task 2: Pipeline and retrieval integration

**Files:** Modify `scenario_import_pipeline.py`, `scenario_documents.py`, `agents/knowledge_base.py`, `scripts/reindex-scenarios.py`; add integration tests.

- [ ] Trigger OCR only when PDF text extraction is empty; merge OCR blocks with page/confidence source metadata.
- [ ] During `embedding`, batch chunks through the configured provider, persist vectors in JSON and Qdrant, and record `vector_backend`, `embedding_model`, and warnings in job metadata.
- [ ] Make `KnowledgeBaseService.search` query Qdrant when healthy, otherwise load JSON index; always apply existing hard filters before scoring.
- [ ] Make reindex idempotent and write both JSON and Qdrant collections, with a `--no-vector` switch for offline operation.

### Task 3: Operations, health, and documentation

**Files:** Create `backend/trpg_server/routes/vector_health.py`; modify `app_factory.py`, `README.md`, `docs/api.md`, `docs/scenario-import.md`; add health tests.

- [ ] Add protected `GET /api/vector/health` returning Qdrant, embedding, OCR status and active configuration without secrets.
- [ ] Register provider singletons in `app.extensions`; close clients on teardown.
- [ ] Document Docker startup, model download/cache locations, environment variables, API examples, fallback behavior, and backup/restore of Qdrant plus JSON indexes.
- [ ] Run `pytest -q`, `npm run typecheck`, `npm run build:frontend`, `scripts/verify.ps1`, and `git diff --check`.
