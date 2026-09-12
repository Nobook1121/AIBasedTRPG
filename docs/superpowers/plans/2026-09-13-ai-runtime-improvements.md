# AI Runtime Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在保持现有 TRPG 房间、剧本模块和工具兼容的前提下，完成分层 Prompt、外置房间状态、小模型配置、结构化输出、缓存遥测和每日 token 看板。

**Architecture:** 通过独立的 prompt builder、room state/telemetry 服务和结构化响应适配层连接现有 Flask chat route；旧数据采用回退读取，默认 provider 请求仍兼容 OpenAI-compatible API。前端复用现有消息 metadata、ConfigManager 和设置 API。

**Tech Stack:** Python 3.11、Flask、JSON 文件存储、pytest、TypeScript、原生 HTML/CSS。

**Spec:** `docs/superpowers/specs/2026-09-13-ai-runtime-improvements-design.md`

## Global Constraints

- 静态 Prompt 层不得包含房间 ID、玩家名、时间戳、随机数或动态状态。
- 状态更新必须由后端白名单校验并执行，AI 不直接写状态。
- 旧房间数据和旧的纯文本 AI 回复必须继续可读。
- 新增配置、日志、运行数据遵循现有 `data/config`、`data/runtime`、`backend/trpg_server` 结构。
- 不新增强制外部服务依赖；provider 继续使用 OpenAI-compatible 请求。

---

### Task 1: Add deterministic prompt layers and cache key

**Files:**
- Create: `backend/trpg_server/agents/prompt_builder.py`
- Test: `tests/test_prompt_builder.py`

**Interfaces:**
- Produce `PromptLayers` dataclass with `messages: list[dict[str, str]]`, `cache_key: str`, `static_prefix: str`.
- Produce `build_prompt_layers(global_rules, scenario, scene, room_state, history, user_input, rules_version="1")`.

- [ ] **Step 1: Write failing tests** asserting fixed layer order, dynamic values appear only after static layers, and cache key excludes room ID.
- [ ] **Step 2: Run `pytest tests/test_prompt_builder.py -q` and confirm failure because the module is missing.**
- [ ] **Step 3: Implement deterministic serialization, version extraction, static prefix and dynamic messages.**
- [ ] **Step 4: Run the focused tests and then `pytest -q`.**
- [ ] **Step 5: Commit `feat: add deterministic prompt layer builder`.**

### Task 2: Externalize room state and event history

**Files:**
- Create: `backend/trpg_server/agents/room_state.py`
- Modify: `backend/trpg_server/agents/context.py`
- Modify: `backend/trpg_server/routes/chat.py`
- Test: `tests/test_room_state.py`

**Interfaces:**
- `load_room_state(room_dir) -> dict[str, Any]`
- `save_room_state(room_dir, state) -> dict[str, Any]`
- `project_room_state(state, snapshot) -> dict[str, Any]`
- `append_room_event(room_dir, event) -> dict[str, Any]`

- [ ] **Step 1: Write failing tests for default state, atomic persistence, event log truncation and dynamic projection.**
- [ ] **Step 2: Run focused tests and confirm expected missing-module failures.**
- [ ] **Step 3: Implement state normalization, atomic JSON writes and bounded rolling summary/event log.**
- [ ] **Step 4: Integrate `AgentRequestContext.room_state()` and chat route loading without changing old history files.**
- [ ] **Step 5: Run focused and full Python tests.**
- [ ] **Step 6: Commit `feat: externalize room state and event log`.**

### Task 3: Add structured KP response validation and safe state execution

**Files:**
- Create: `backend/trpg_server/agents/structured_output.py`
- Modify: `backend/trpg_server/agents/runtime.py`
- Modify: `backend/trpg_server/routes/chat.py`
- Test: `tests/test_structured_output.py`

**Interfaces:**
- `parse_kp_response(content) -> StructuredKPResponse | None`
- `validate_state_updates(updates, room_state, scenario) -> dict[str, Any]`
- `apply_state_updates(room_dir, updates) -> dict[str, Any]`

- [ ] **Step 1: Write failing tests for valid JSON, fenced JSON, malformed fallback, unknown field removal, and invalid scene rejection.**
- [ ] **Step 2: Run focused tests and verify they fail before implementation.**
- [ ] **Step 3: Implement tolerant JSON extraction and strict field/state whitelist validation.**
- [ ] **Step 4: Integrate chat route to use `narration` as visible content, execute validated updates, and preserve plain text fallback.**
- [ ] **Step 5: Run all Python tests.**
- [ ] **Step 6: Commit `feat: validate structured KP output safely`.**

### Task 4: Add small-model task configuration

**Files:**
- Modify: `backend/trpg_server/agents/config.py`
- Modify: `backend/trpg_server/role_config.py`
- Modify: `backend/trpg_server/routes/config.py`
- Modify: `data/config/aiplatform/aliyun.json`
- Modify: `data/config/aiplatform/deepseek.json`
- Create: `data/config/aiplatform/openai.json`
- Modify: `data/config/general.toml`
- Test: `tests/test_small_model_config.py`

**Interfaces:**
- `AIRuntimeConfig.small_model_tasks: dict[str, str]`
- `provider_small_model_config(provider_config, task) -> dict[str, Any]`

- [ ] **Step 1: Write failing tests for task defaults, provider model selection and OpenAI config shape.**
- [ ] **Step 2: Run focused tests and observe failure.**
- [ ] **Step 3: Implement config parsing and provider helper with fallback to the primary model.**
- [ ] **Step 4: Add conservative default small models for Bailian (`qwen-turbo`), DeepSeek (`deepseek-chat`) and OpenAI (`gpt-4o-mini`) without enabling new providers automatically.**
- [ ] **Step 5: Run full Python tests.**
- [ ] **Step 6: Commit `feat: configure small model task routing`.**

### Task 5: Add cache and token telemetry aggregation

**Files:**
- Create: `backend/trpg_server/agents/telemetry.py`
- Modify: `backend/trpg_server/settings.py`
- Modify: `backend/trpg_server/routes/chat.py`
- Create: `backend/trpg_server/routes/telemetry.py`
- Modify: `backend/trpg_server/app_factory.py`
- Test: `tests/test_ai_telemetry.py`

**Interfaces:**
- `record_ai_usage(log_dir, usage) -> dict[str, Any]`
- `load_daily_ai_usage(log_dir, day=None) -> dict[str, Any]`
- `calculate_cache_hit_rate(prompt_tokens, cached_tokens) -> float`
- `build_provider_cache_key(scenario_id, scenario_version, scene_id, scene_version, rules_version) -> str`

- [ ] **Step 1: Write failing tests for cache-key stability, rate clamping, daily role aggregation and future role IDs.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement append-only daily JSONL/JSON telemetry storage and aggregation.**
- [ ] **Step 4: Add `/api/telemetry/ai/daily` GET endpoint with existing settings permission guard.**
- [ ] **Step 5: Include usage metadata in chat response and `log_user_action`; measure elapsed time around provider completion.**
- [ ] **Step 6: Run full Python tests.**
- [ ] **Step 7: Commit `feat: add AI usage telemetry and cache metrics`.**

### Task 6: Display cache metrics and daily token dashboard

**Files:**
- Modify: `frontend/src/types/room.d.ts`
- Modify: `frontend/src/app/chat.ts`
- Modify: `frontend/src/templates/chat.html`
- Modify: `frontend/src/index/fragments/03-room-tools-auth-settings.html`
- Modify: `frontend/src/app/tabs.ts`
- Modify: `frontend/src/app/config/ConfigManager.ts`
- Modify: `frontend/src/locales/zh_cn.json`
- Modify: `frontend/src/locales/en_us.json`
- Test: `tests/test_frontend_ai_telemetry.py`

**Interfaces:**
- Chat metadata fields: `tokenCount`, `cacheHitRate`, `cachedTokens`, `processingTime`.
- Dashboard loader calls `/api/telemetry/ai/daily` and renders arbitrary `agent_id` rows.

- [ ] **Step 1: Write failing source-contract tests for metadata rendering, settings markup, API path and role-agnostic aggregation.**
- [ ] **Step 2: Run focused tests and confirm failure.**
- [ ] **Step 3: Implement processing text with cache hit rate and pass metadata through persisted room messages.**
- [ ] **Step 4: Add dashboard panel, loader, empty/error states and translations.**
- [ ] **Step 5: Run `npm run typecheck` and Python frontend contract tests.**
- [ ] **Step 6: Commit `feat: show AI cache metrics and token dashboard`.**

### Task 7: End-to-end regression verification

**Files:**
- Modify only if needed after test evidence.

- [ ] **Step 1: Run `pytest -q` and record the complete result.**
- [ ] **Step 2: Run `npm run typecheck` and `npm run build:frontend`.**
- [ ] **Step 3: Inspect `git diff --check` and verify no secrets or unrelated files changed.**
- [ ] **Step 4: Re-read the spec and check every requirement against implemented files/tests.**
- [ ] **Step 5: Commit only if verification is clean: `chore: verify AI runtime improvements`.**
