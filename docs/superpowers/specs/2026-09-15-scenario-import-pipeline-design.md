# 剧本文档异步导入与知识库 Pipeline 设计

## 目标

在不替换现有 Flask、JSON 文件存储、剧本模块编辑器、房间版本绑定和
`KnowledgeBaseService` 的前提下，实现从 Word、PDF、TXT、Markdown 文档到可审核剧本、
版本化知识索引和正式发布剧本的完整流程。

核心验收范围：

- 上传 `.docx`、`.pdf`、`.txt`、`.md` 文档并持久化原文件。
- 后台执行解析、切块、抽取、合并、卡片化、总结和索引阶段。
- 页面显示真实后端进度，刷新后可恢复，失败阶段可重试，任务可取消。
- 完成后复用现有剧本模块编辑器审核卡片，编辑后发布。
- 发布结果保留来源引用、剧本版本和知识索引；旧房间继续使用绑定的旧版本。
- 检索前强制按剧本、版本、场景、剧透等级和受众过滤。

## 现有能力与复用边界

复用以下实现：

- `scenario_importer.py` 已有 DOC/DOCX/TXT/Markdown 文本提取、标题识别、模块转换和 AI
  JSON 转换兜底。
- `ScenarioModule` 和现有编辑器已经覆盖背景、公开信息、准备、时间线、场景、结局、
  NPC、怪物和自定义模块，继续作为剧本卡片的编辑与发布模型。
- `scenario_store.py` 已有规范化、原子写入、版本快照和发布时知识索引持久化。
- 房间 `info.json` 已绑定 `scenario_id + scenario_version`，并记录当前场景和剧透等级。
- `KnowledgeBaseService.search(room_id, query)` 已提供业务层统一入口和检索前硬过滤。
- 前端现有剧本创建模态框已经支持模块编辑、删除、排序、草稿保存和最终创建。

扩展而不重写：

- 把同步导入接口保留为兼容入口，新上传 UI 改用异步任务接口。
- 为现有模块补充知识卡片元数据，不建立第二套互相转换的卡片数据库。
- 把词法检索保留为无配置兜底，在同一服务接口内增加 embedding 排序。
- 不改变房间读取已绑定版本的方式；发布新版本不会自动迁移旧房间。

## 参考项目使用原则

需求指定参考 `https://github.com/ACDD49967/TRPG-AI-DM` 的 RAG 和节省 token 方法。
当前执行环境的网页检索、GitHub 代理和 GitHub 直连均不可用，因此无法可靠核对该仓库的
具体源码，也不会声称复制了其中的实现。本文采用该类项目通用且与本仓库需求明确一致的
方法：分层切块、离线结构化、持久化检索索引、检索前元数据过滤、只向模型注入 top-k
相关卡片，以及全局摘要作为稳定 Prompt 前缀。网络恢复后可在不改变下面接口的情况下核对
embedding、融合检索和摘要策略。

## 架构

```text
上传 UI
  -> POST /api/scripts/import
  -> ImportJobStore + 后台线程执行器
       -> parsing      文档 -> 层级 Markdown
       -> chunking     标题优先切块 + 字符重叠
       -> extracting   本地结构抽取 + 可选逐块 LLM 增强
       -> merging      实体别名归并、时间线去重、冲突保留
       -> carding      转为扩展后的 ScenarioModule/KnowledgeCard
       -> summarizing  全局摘要 + 章节摘要 + 卡片短描述
       -> embedding    embedding 或确定性词法向量兜底
  <- GET job / SSE stream
  -> 现有剧本编辑器审核
  -> POST /api/scripts/<script_id>/publish
  -> scenario.json + versions/<version>.json + knowledge-index/<version>.json
  -> 新房间默认绑定最新版本；旧房间保持原版本
```

## 持久化布局

导入任务新增目录：

```text
data/runtime/scenario_imports/<job_id>/
  job.json
  source/<安全化文件名>
  intermediate/parsed.json
  intermediate/chunks.json
  intermediate/extractions.json
  intermediate/merged.json
  intermediate/cards.json
  intermediate/summary.json
```

正式剧本继续使用：

```text
data/scenarios/scenario-<script_id>/
  scenario.json
  versions/<script_version>.json
  knowledge-index/<script_version>.json
  source/<发布时保留的原始文件>
  imports/<job_id>/manifest.json
```

导入任务只属于创建者；读取、重试、取消和发布都需要登录、任务所有权及现有剧本权限。
发布成功后任务保留为审计记录，不删除中间结果。

## ImportJob 模型

`job.json` 至少包含：

- `id`、`owner_id`、`script_id`、`target_version`、`source_filename`。
- `status`：`pending / parsing / chunking / extracting / merging / carding /
  summarizing / embedding / done / failed / cancelled / published`。
- `progress`、`current_stage`、`stage_progress` 和 `stage_meta`。
- `error`、`failed_stage`、`retry_count`、`cancel_requested`。
- 各中间文件的相对路径和精简预览。
- `created_at`、`started_at`、`updated_at`、`completed_at`。

每次状态更新使用 `write_json_atomic`。服务重启时，未完成任务标为可重试的 `failed`，不伪装为
仍在运行。单进程内使用受锁保护的 `ThreadPoolExecutor`；这个选择符合当前单机 Flask 产品形态，
且不要求部署 Redis。未来迁移到 Celery 时保持 JobStore 和 API 契约不变。

## 文档解析与切块

- TXT/Markdown：UTF-8 BOM、UTF-8、GB18030 依次尝试，保留标题和段落。
- DOCX：扩展现有 OOXML 读取，保留 Heading 层级、列表和表格文本。
- PDF：新增 PyMuPDF。输出页码、文本块、字体大小和推断标题层级。选择它是因为单一依赖即可
  提供文本、页码和字体信息，适合当前需求。
- 扫描 PDF：本次不引入 PaddleOCR。若页面几乎无文本，任务以可重试错误结束，并明确提示需要
  OCR；解析器保留 OCR provider 接口，避免以后改变 Pipeline。
- 上传上限调整为可配置的 32 MiB，前后端同时校验扩展名和大小。
- 标题优先形成章节；无结构文本按段落聚合为 800～1500 个 Unicode 字符，邻块保留
  100～200 字重叠。每块记录稳定 `chunk_id`、页码范围、章节路径和原始文本。

## 结构化抽取、合并和卡片化

逐块抽取输出地点、NPC、事件、线索、时间线、主线和未决问题。所有实体必须带 `source_quote`
和 `source_ref`；只抽取原文明示内容，不确定值使用 `null`。

AI 平台可用时复用现有平台配置和结构化 JSON 请求方式。单块失败不会丢弃整份文档：记录失败块，
本地模块结果继续生成，任务最终标记警告。无 AI 配置时完整执行确定性本地 Pipeline。

合并规则：

- 规范化名称后归并同名实体，把别名放入 `metadata.aliases`。
- 事件按明确时间或来源顺序排序并去重。
- 冲突值都保留在 `metadata.conflicts`，不自动二选一。
- 只在证据明确时解析代词；否则保留原文本和未决问题。
- 大文档先按章节分组合并，再执行全局合并，避免一次 Prompt 包含全部原文。

现有 `ScenarioModule` 扩展以下可选字段：

- `card_type`、`scene_id`、`spoiler_level`、`unlock_condition`。
- `source_ref: {page, page_end, chapter, quote, chunk_id}`。
- `metadata: {aliases, conflicts, parent_location, extraction_warnings}`。
- `script_version` 和 `embedding` 只在索引中持久化；编辑器不直接传输大型向量数组。

全局摘要保存为 `core` 类型的知识卡，同时写入剧本的 `global_summary`。Prompt 构建只注入全局摘要、
当前场景摘要和 top 3～5 检索卡片，避免重新发送全文。

## Embedding 与检索

引入一个小型 `EmbeddingProvider` 接口：

- 优先调用现有 OpenAI 兼容平台的 `/embeddings` 能力，模型名通过环境或现有平台配置指定。
- 未配置 embedding 模型时使用确定性 hashed token 向量作为本地兜底；它不需要下载模型，适合
  测试和离线运行，但语义能力有限。
- 索引继续保存为每个剧本版本一个 JSON 文件，不新增 Chroma、Milvus 或数据库服务。

检索顺序固定为：

1. 按 `scenario_id + scenario_version` 过滤。
2. 按当前场景、剧透等级、受众可见性和已满足解锁条件过滤。
3. 计算向量余弦分数和现有词法分数。
4. 用加权融合排序；专有名词精确命中获得小幅加权。
5. 返回 top 3～5 卡片，并带来源引用。

本次不引入 reranker。数据规模和单机部署尚不足以抵消额外模型调用、延迟与配置复杂度。

## API

新增并保留 `/api` 前缀：

- `POST /api/scripts/import`：multipart 上传并返回 `202 + jobId + scriptId`。
- `GET /api/scripts/import/<job_id>`：任务详情和中间结果摘要。
- `GET /api/scripts/import/<job_id>/stream`：SSE 进度；发送完整快照和心跳。
- `POST /api/scripts/import/<job_id>/retry`：从 `failed_stage` 或请求的合法阶段继续。
- `POST /api/scripts/import/<job_id>/cancel`：设置取消标记。
- `PUT /api/scripts/import/<job_id>/preview`：保存审核页对卡片和摘要的修改。
- `POST /api/scripts/<script_id>/publish`：校验任务归属和预览内容后发布。
- `GET /api/scripts/<script_id>/versions`：返回版本和发布时间列表。
- `POST /api/scripts/<script_id>/search`：仅供受保护的调试/内部调用。

现有 `/api/scenarios/import` 保留同步文本转换兼容性，不再由新上传 UI 使用。现有
`POST /api/scenarios` 和 `PUT /api/scenarios/<id>` 继续服务手工创建与编辑。

## 前端流程

剧本页新增导入模态框：

- 拖放区和文件选择器。
- 剧本名称、简介、作者和是否公开。
- 扩展名、大小和空文件即时校验。
- XMLHttpRequest 上传进度与后端处理进度分开显示。

处理视图展示八个阶段、总进度、当前块计数、错误信息、取消和重试。优先使用 SSE；断线后自动
重连，并以 `GET job` 轮询兜底。任务 ID 保存在 `sessionStorage`，刷新剧本页后重新加载后端状态。

任务完成后把 `global_summary + cards` 填入现有剧本编辑器。现有模块编辑、删除和排序能力直接
复用；补充类型、剧透等级、来源引用和冲突提示。发布操作二次确认并调用发布 API。合并、拆分和
按类型重新生成属于增强项：在本次核心交付中保留后端接口边界和明确的后续增强标记，不阻塞最小验收。

## 错误处理

- 不支持格式、空文件或超过上限：上传前后都拒绝。
- 解析失败：保留原文件，记录可读原因和 `failed_stage=parsing`。
- 单块 AI 失败：记录块 ID，可重试 extracting；已有成功块不重跑。
- Provider 超时：采用现有本地转换兜底并记录 warning。
- 取消：阶段边界和逐块循环检查取消标记，已生成中间文件保留。
- 重试：从最近有效中间文件继续，不能跳过缺少依赖输出的阶段。
- 发布失败：不改变任务为 published，也不留下半写入剧本；正式剧本继续使用原子写入。

## 测试与验收

后端测试：

- TXT、Markdown、DOCX 和含文本 PDF 的解析与来源页码。
- 标题优先切块、无标题长文本切块和 overlap。
- Job 状态持久化、SSE 快照、刷新查询、取消和指定阶段重试。
- 两个相似剧本交叉查询不串库。
- 场景、版本、剧透、可见性和解锁条件均在评分前过滤。
- 发布创建版本快照、原始文件和知识索引；旧房间绑定不变化。
- 无 AI、AI 超时和单块失败仍保留原文并产生可审核结果。

前端测试与静态约束：

- 拖放、点击、格式、大小和上传状态。
- 阶段名称、百分比、块计数、断线轮询和刷新恢复。
- 完成后进入现有编辑器，显示来源和冲突，发布需要二次确认。
- TypeScript 类型检查和完整前端构建。

完成前运行：

```powershell
pytest -q
npm run typecheck
npm run build:frontend
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1
git diff --check
```

## 明确限制

- 扫描 PDF 的 OCR 只留扩展点和明确提示，本次不打包 PaddleOCR。
- JSON 索引适合当前单机规模；卡片量达到数十万或需要多机共享时再迁移向量数据库。
- 本地 hashed token embedding 是离线兜底，不宣称达到云端语义模型效果。
- 合并、拆分、分类重生成作为后续增强项，不阻塞上传、真实进度、审核、发布和隔离检索主流程。
