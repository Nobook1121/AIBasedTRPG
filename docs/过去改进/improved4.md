# 任务：将向量数据库完全内嵌到程序中，移除对外部软件的依赖

你是一位资深后端工程师。项目是一个 AI 跑团网页游戏，房间管理、剧本分块、知识库（RAG）、导入 pipeline 均已实现，当前使用 **Qdrant** 作为向量数据库（支持 Python 本地持久化模式）。

**本次目标**：把向量数据库从 Qdrant 迁移为**真正内嵌到程序进程内、无任何外部软件依赖**的嵌入式方案，并保留 Qdrant 作为可选后端。用户不希望安装 Qdrant、Docker 或其他外部服务。

**重要参考**：在“C:\Mine\AI-TRPG-GM”路径下存在一个和我这个项目类似目标的项目，尝试参考学习这个项目的知识库等对剧本的处理方式，如果他有好的本地embedding模型，提示词啥的可以直接复制过来用。
**另附注意**：鉴于有些剧本比较大，尝试将每个剧本的向量数据库保存到对应剧本的剧本文件夹中，不要全部保存在一个向量数据库中。另外对于从外部导入剧本，提供两个导入选项，直接导入和可编辑导入，直接导入则不按照现在的模块系统生成模块，而是直接生成到向量数据库，用户点击预览可以看到这个剧本的向量数据库中的向量树，并且提供一个上传窗口，可以上传预览这个剧本中所用到的线索（线索可能为图片，视频等）。最后，对所有旧的房间还有剧本进行归档并且删除（归档仅需保存到本地，无需commit到github。）

---

## 1. 现状与边界

**已有，需要保留**：
- 知识库检索流程（硬过滤 + 向量检索 + 词法分数融合）
- Embedding 三级兜底：本地模型 → OpenAI-compatible → 本地哈希
- 剧本卡片数据模型与元数据
- 版本化（n.n.n）、剧本快照、JSON 知识索引
- 异步导入任务与进度
- PaddleOCR 扫描 PDF
- 阿里云百炼 AI 平台接入

**需要改造**：
- 向量存储层：从 Qdrant 改为**嵌入式默认后端**
- 配置与文档：明确“零外部依赖”的默认启动路径
- 保留 Qdrant 作为可选后端（当 `AI_TRPG_VECTOR_DB_URL` 配置时才启用）

**不要重写已有可用模块**，优先兼容改造；冲突处记录原因。

**你可以自行决定**：
- 嵌入式向量库选型（**推荐 ChromaDB**，其他可选：Zvec、sqlite-vector、PolarisDB、LEANN、Vectra 等，说明理由）
- 是否使用 SQLite + 向量扩展作为底层存储
- 是否保留 Qdrant 适配器作为可选后端
- 是否将 JSON 知识索引与嵌入式向量库合并，或继续双写

---

## 2. 核心要求

### 2.1 默认零外部依赖

- 项目自身即可运行，不需要 Docker、不需要 Qdrant 服务、不需要任何外部软件
- 向量化、存储、检索全部在进程内完成
- 数据持久化到本地目录（沿用现有 `data/runtime/vector-db/` 路径风格，改为 `data/runtime/vector-db/embedded/` 或类似）
- 首次启动自动初始化，无需手动建表或迁移

### 2.2 保留现有能力

迁移后以下能力必须保持不变或更强：

- 硬过滤：`script_id + script_version + scene_id + spoiler_level`
- 向量检索 + 词法分数融合
- Embedding 三级兜底
- 元数据过滤与排序
- 剧本间隔离
- 版本化：不同版本独立索引，旧版本保留
- 多房间共享同一剧本版本索引

### 2.3 抽象层设计

请设计一个**向量存储抽象接口**（如 `VectorStore`），至少包含：

- `upsert(chunks: KnowledgeChunk[])`
- `delete(ids: string[])`
- `deleteByFilter(filter: Record<string, any>)`
- `query(vector: number[], filter: Record<string, any>, topK: number): ChunkResult[]`
- `count(filter?: Record<string, any>)`

然后提供至少两个实现：

1. **EmbeddedVectorStore**（默认）：基于嵌入式向量库
2. **QdrantVectorStore**（可选）：当 `AI_TRPG_VECTOR_DB_URL` 配置时启用

业务层只依赖抽象接口，切换后端不改业务代码。

### 2.4 嵌入式向量库选型建议

**首选 ChromaDB**：
- `pip install chromadb` 即可，内置嵌入函数，支持元数据过滤
- `PersistentClient(path=...)` 直接本地持久化
- 与现有 LangChain / LlamaIndex 生态兼容

如果因体积、性能或平台限制不选 ChromaDB，可考虑：
- **Zvec**：阿里开源，支持稠密+稀疏向量，Rust 核心
- **sqlite-vector**：复用 SQLite 生态，单文件存储
- **LEANN**：存储空间极省，适合大文档
- **PolarisDB** / **Vectra**：按语言栈选择

请在 README 中说明选型理由与替代方案。

### 2.5 迁移与兼容

- 提供从现有 JSON 知识索引 / Qdrant 迁移到嵌入式库的脚本或启动时自动导入
- 旧数据目录 `data/scenarios/scenario-<id>/knowledge-index/<version>.json` 继续作为人类可读备份，或作为嵌入式库的持久化格式之一
- 配置项兼容：`AI_TRPG_VECTOR_DB_URL` 不设置时用嵌入式；设置时用 Qdrant
- 环境变量新增默认值：`AI_TRPG_VECTOR_BACKEND=embedded | qdrant`，默认 `embedded`

### 2.6 性能与规模

- 单剧本 5 万字以上、卡片数百到数千，检索应在毫秒级
- 多剧本累计数万卡片，仍需可用
- 如选型有存储或内存上限，请在 README 说明适用规模

---

## 3. 具体改造点

### 3.1 依赖

- `requirements.txt`：把 `qdrant-client` 从主依赖改为可选依赖，移入 `requirements-vector-qdrant.txt`
- 主依赖加入嵌入式向量库（如 `chromadb`）
- 保留 `requirements-vector.txt` 作为“启用 Qdrant”的补充依赖

### 3.2 向量存储层

- 新建 `VectorStore` 抽象接口
- 实现 `EmbeddedVectorStore`（默认）
- 保留/改造 `QdrantVectorStore`（可选）
- 工厂函数根据 `AI_TRPG_VECTOR_BACKEND` 或 URL 配置选择实现
- 现有调用点改为依赖抽象接口

### 3.3 数据路径

- 嵌入式库默认路径：`data/runtime/vector-db/embedded/`
- Qdrant 本地路径保留：`data/runtime/vector-db/qdrant/`
- JSON 知识索引继续保留：`data/scenarios/scenario-<id>/knowledge-index/<version>.json`
- 首次启动自动创建目录与集合

### 3.4 配置

- 新增 `AI_TRPG_VECTOR_BACKEND`（`embedded` / `qdrant`，默认 `embedded`）
- 保留 `AI_TRPG_VECTOR_DB_URL`，设置时自动切到 Qdrant
- 保留现有 `AI_TRPG_OCR_*`、Embedding 相关配置
- 更新 `data/config/` 与 `.env.example`

### 3.5 文档

- README 明确写出：
  - **默认零外部依赖启动步骤**：`pip install -r requirements.txt` → 直接运行
  - **可选 Qdrant 后端**：需要时如何安装与配置
  - **Docker Qdrant 高级部署**：保留原说明
  - **Embedding 三级兜底**：顺序与配置方式
  - **PaddleOCR**：模型缓存与启用方式
  - **数据目录说明**：剧本、版本快照、知识索引、向量库、异步任务
  - **迁移说明**：从旧版本升级时数据如何处理

---

## 4. UI 影响（导入进度）

上传导入的 UI（进度提示、卡片预览、审核、发布）已实现，本次不要求改 UI，但需确认：

- 后端进度推送（SSE / WebSocket / 轮询）在切换向量后端后仍正常工作
- 导入流程中“向量入库”阶段的进度百分比与阶段名保持一致
- 失败重试阶段名与后端阶段枚举一致

如无 UI 改动，仅记录本次后端改造对前端**无 breaking change**。

---

## 5. 测试与验收

**功能测试**：
- 不设置任何 Qdrant 相关环境变量，`pip install -r requirements.txt` 后直接启动，跑通导入 → 检索 → 开房间
- 用 5 万字 Word + 扫描版 PDF 各跑一次完整导入
- 检索验证：`script_id + script_version + scene_id + spoiler_level` 过滤生效

**隔离测试**：
- 构造两个相似剧本（都有灯塔、失踪、邪教），交叉提问，top-k 不含其他 `script_id`
- 同剧本不同版本，检索不串
- 未解锁线索不被检索

**兼容测试**：
- 设置 `AI_TRPG_VECTOR_DB_URL`，切换到 Qdrant 后端，功能保持一致
- 从旧数据（JSON 索引 / Qdrant）迁移到嵌入式库，卡片数量与检索结果一致

**性能测试**：
- 单剧本 1000 卡片检索延迟 < 50ms（本地）
- 多剧本累计 1 万卡片检索延迟 < 200ms

**回归测试**：
- 现有 166 个 pytest 用例继续通过
- `npm run typecheck`、`npm run build:frontend`、`scripts/verify.ps1`、`git diff --check` 通过

---

## 6. 交付要求

- **尽量不重写已有可用模块**，优先兼容改造；冲突处记录原因
- 改动前先输出**改造计划**：哪些复用、哪些扩展、哪些新建
- 抽象接口清晰，后端可插拔
- README 更新：技术选型理由、架构图、默认启动路径、可选后端、配置项、数据目录、迁移说明
- 现有测试全部通过，新增向量后端相关测试
- 遇到规格未覆盖处，做合理假设并记录

---

## 7. 落地步骤建议

1. 阅读现有向量存储与检索代码，明确调用点
2. 设计 `VectorStore` 抽象接口
3. 选型并集成嵌入式向量库
4. 实现 `EmbeddedVectorStore`，替换默认后端
5. 把 Qdrant 改造为可选实现
6. 编写迁移脚本或启动时自动导入
7. 更新配置、依赖、文档
8. 跑全量测试与验收
9. 输出改造总结：改动点、默认启动路径、可选后端切换方式

请先给出你的改造计划，再开始实现。