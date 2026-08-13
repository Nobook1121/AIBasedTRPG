# AI Provider Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AnythingLLM as a built-in AI provider and let admins create custom providers using OpenAI, Anthropic, or custom request mappings.

**Architecture:** Provider JSON remains the source of truth, but provider loading becomes dynamic instead of hard-coded. Backend chat/test code gains small protocol adapters for OpenAI-compatible, Anthropic, and custom response extraction, while the existing platform settings UI adds a custom-provider modal.

**Tech Stack:** Flask, Python `requests`, TypeScript frontend, static JSON provider configs, pytest, TypeScript compiler.

---

### Task 1: Backend Provider Protocol Helpers

**Files:**
- Modify: `trpg_server/routes/chat.py`
- Modify: `trpg_server/routes/config.py`
- Test: `tests/test_ai_provider_protocols.py`

- [ ] **Step 1: Write failing tests**

Add tests that verify OpenAI URL resolution, Anthropic request conversion, AnythingLLM OpenAI-compatible response parsing, and custom response-path extraction.

Run: `pytest tests/test_ai_provider_protocols.py -v`
Expected: FAIL because the helper functions do not exist.

- [ ] **Step 2: Implement helpers**

Add helpers for:
- `provider_api_format(config)` with default `"openai"`.
- `resolve_provider_endpoint(config)` using `config.config.endpoint_url` when present, otherwise normalizing `base_url`.
- `build_provider_request(config, payload)` for OpenAI, Anthropic, and custom.
- `extract_provider_text(config, response_data)` for OpenAI, Anthropic, AnythingLLM-compatible OpenAI, and `custom.response_path`.

- [ ] **Step 3: Wire chat and test routes**

Use the helpers in `/api/chat` and `/api/config/aiplatform/<platform>/test`, preserving existing behavior for current providers.

- [ ] **Step 4: Run backend tests**

Run: `pytest tests/test_ai_provider_protocols.py tests/test_chat_agent_context.py -v`
Expected: PASS.

### Task 2: Dynamic Provider Loading And AnythingLLM Config

**Files:**
- Modify: `frontend/src/js/config/AIPlatformManager.ts`
- Modify: `frontend/src/js/types.d.ts`
- Modify: `trpg_server/routes/config.py`
- Create: `data/config/aiplatform/anythingllm.json`

- [ ] **Step 1: Add provider listing endpoint**

Add `GET /api/config/aiplatforms` returning the JSON platform configs from `data/config/aiplatform/*.json`, excluding `default-request.json`.

- [ ] **Step 2: Update frontend loading**

Change `AIPlatformManager.loadPlatforms()` to call `/api/config/aiplatforms` and store returned configs by `platform`.

- [ ] **Step 3: Add AnythingLLM config**

Create `anythingllm.json` with `api_format: "openai"`, `base_url: "http://localhost:3001/api/v1/openai/chat/completions"`, and a model whose id is the workspace slug placeholder.

- [ ] **Step 4: Run typecheck**

Run: `npm run typecheck`
Expected: PASS.

### Task 3: Custom Provider UI

**Files:**
- Modify: `frontend/src/index/fragments/03-room-tools-auth-settings.html`
- Modify: `frontend/src/js/platform-ui.ts`
- Modify: `frontend/src/styles/03-tools-settings-platform.css`
- Modify: `frontend/src/js/types.d.ts`

- [ ] **Step 1: Add modal markup**

Add an "Add provider" button near the AI platform list and a Bootstrap modal with fields for provider name, id, interface spec, API key, base URL, endpoint URL, model id/name, custom headers JSON, custom request JSON, and response path.

- [ ] **Step 2: Bind modal behavior**

Add frontend handlers that validate required fields, generate an `AIPlatformConfig`, save it with `aiPlatformManager.savePlatformConfig()`, reload providers, and refresh role provider options.

- [ ] **Step 3: Preserve existing provider config modal**

Show interface spec fields in platform config. Do not force `/v1/chat/completions` onto Anthropic, AnythingLLM, or custom endpoints.

- [ ] **Step 4: Run frontend build**

Run: `npm run build:frontend`
Expected: PASS.

### Task 4: Full Verification

**Files:**
- Modify only as needed based on failing verification.

- [ ] **Step 1: Run automated checks**

Run: `pytest -q`
Expected: PASS.

Run: `npm run typecheck`
Expected: PASS.

Run: `npm run build:frontend`
Expected: PASS.

- [ ] **Step 2: Manual sanity checks**

Start the app, open AI platform settings, confirm AnythingLLM appears, custom provider modal saves a provider, and role provider dropdown includes enabled custom providers.
