# 任务：实现“上传文件 → 自动生成知识库与剧本卡”的导入 Pipeline（含 UI 进度提示）

你是一位资深全栈工程师。这是一个**已有大部分实现的 AI 跑团网页游戏项目**，房间管理和剧本分块系统已落成部分，但**知识库部分缺失**。请先阅读现有代码结构、数据模型、剧本分块逻辑、房间绑定方式、前端技术栈与 UI 组件库，再实现以下功能。

**尽量不要重写可用模块**。技术栈（前后端）以现有项目为准，不要擅自更换。若需新增依赖（文档解析、向量库、embedding、任务队列等），请说明理由。

**RAG与省token方案等可以参考“https://github.com/ACDD49967/TRPG-AI-DM”github项目库！！！！该项目已经大部分实现了我设想到的内容**

---

## 0. 现状与边界

**已有，需要复用/对接**：
- 房间管理（房间绑定剧本）
- 剧本分块系统（已有分块逻辑，可能不是卡片化）
- 剧本数据结构
- 前端框架与 UI 组件库（请先阅读并沿用）
- 剧本卡片的创建与结构

**完全缺失，需要你新建**：
- 文档上传与解析（Word / PDF / TXT / Markdown）
- 两阶段导入 pipeline
- 知识库（RAG）：向量化、入库、检索、过滤（已有部分，请优化缺失）
- 全局总纲 + 分层摘要
- 异步任务与进度查询
- **导入 UI：上传、进度提示**

**你可以自行决定**：
- 文档解析库（`python-docx` / `mammoth` / `pdfplumber` / `PyMuPDF` / OCR 选型）
- 向量库（ChromaDB / Milvus / DashVector / pgvector）（优先使用已有的）
- Embedding 模型（本地 bge / DashScope / OpenAI）（优先保留已有的）
- 抽取用 LLM（推荐便宜模型如 DeepSeek / Qwen）（优先保留已实现的）
- 任务队列（BullMQ / Celery / 自建异步任务）
- 进度推送方式（WebSocket / SSE / 轮询，视前端栈决定）
- 是否引入 reranker、BM25、RRF

如果现有分块系统与目标卡片结构冲突，**扩展它而不是重做**，并记录改动。

---

## 1. 目标

用户上传一个文件（Word / PDF / TXT / Markdown，可能 5 万字以上，无严格结构），系统**全自动**处理：

1. 解析文档为结构化文本
2. 生成结构化剧本卡片（地点、NPC、事件、线索、时间线等）（基于已有的剧本卡片系统和剧本模块）
3. 生成全局总纲与分层摘要
4. 弹出剧本创建系统，用户可以在此进行更改与优化生成的内容
5. 用户点击发布后向量化入库

用户尽量不要手动输入内容。**前端必须实时显示处理进度**，完成后可预览确认，再正式发布。

---

## 2. 两阶段 Pipeline

### 阶段一：通用 RAG 处理（机械流程，全自动）（这一块可能已经写好，如果写好了就只要优化即可）

1. **文档解析**
   - Word：`python-docx` / `mammoth`，保留标题层级、段落、列表
   - PDF：`pdfplumber` / `PyMuPDF`，提取文本 + 页码 + 字体大小（推断标题层级）
   - 扫描版 PDF：加 OCR（`PaddleOCR` 中文效果好）
   - 输出带层级标记的 Markdown

2. **章节切分**
   - 优先按标题层级切（章 → 节 → 小节）
   - 无标题时按段落聚合，目标每块 800~1500 字
   - 相邻块保留 100~200 字 overlap
   - 每块记录 `chunk_id`、来源页码/章节、原始文本

3. **Embedding + 入库**（原始向量库，先存一份）
   - 每块生成 embedding
   - 存入向量库，元数据带 `source_doc_id`、页码、章节

### 阶段二：跑团结构化增强（LLM 处理）

在阶段一切分出的文本块基础上：

1. **逐块结构抽取**
   对每块跑一次抽取 prompt，输出 JSON（该json仅作范例，请根据现有模块已经跑团剧本中可能出现的内容进行优化与增加）：
   ```
   {
     "locations": [{"name": "", "description": "", "parent_location": "", "source_quote": ""}],
     "events": [{"name": "", "trigger": "", "outcome": "", "related_location": "", "source_quote": ""}],
     "npcs": [{"name": "", "role": "", "goal": "", "knowledge": [], "source_quote": ""}],
     "clues": [{"name": "", "content": "", "related_event": "", "source_quote": ""}],
     "timeline": [{"order": 1, "event": "", "time_or_condition": ""}],
     "main_plot": "",
     "open_questions": []
   }
   ```
   规则：只抽取原文明确出现的内容，不编造；每条必须带 `source_quote`；不确定填 null。

2. **跨块合并**
   - 同名实体合并，别名归并
   - 事件按时间线排序去重
   - 指代消解（“他”“那里”替换为具体实体）
   - 冲突信息标记 `conflict`，不强行二选一
   - 若一次合并太大，分组两阶段合并

3. **卡片化 + 元数据自动打标**
   转成知识库卡片，LLM 自动推断：
   - `card_type`：`core` / `scene` / `npc` / `clue` / `event` / `rule` / `branch` / `ending`
   - `spoiler_level`：0~5
   - `visibility`：默认 `kp_only`，明确给玩家看的才 `player_visible`
   - `unlock_condition`：玩家需要做什么才能接触
   - `scene_id`：文档无场景时，按地点+时间段生成，如 `loc_lighthouse_day1`
   - 保留 `source_ref`（页码/章节）和 `metadata.aliases`

4. **全局总纲生成**
   - 500~1000 字，含世界观、主线目标、关键 NPC 立场、核心真相、主要分支、结局条件
   - 存为 `card_type = core`，用于 Prompt 前缀，让 AI 始终“知道全部剧情框架”

5. **分层摘要**
   - 总纲（core）
   - 章节摘要（每章 100~200 字）
   - 卡片短描述

6. **版本化入库**
   - 每次导入生成一个 `script_version`（如 `1.0.0`）
   - 所有卡片带 `script_id + script_version`
   - 与现有房间系统对接：新房间默认绑最新版本

---

## 3. 知识库设计（对接已有模块）

### 3.1 卡片数据模型

```typescript
interface KnowledgeChunk {
  id: string;
  scriptId: string;
  scriptVersion: string;
  sceneId?: string;
  cardType: 'core' | 'scene' | 'npc' | 'clue' | 'event' | 'rule' | 'branch' | 'ending';
  visibility: 'kp_only' | 'player_visible';
  spoilerLevel: number;
  unlockCondition?: string;
  text: string;
  embedding: number[];
  sourceRef?: { page?: number; chapter?: string; quote?: string };
  metadata: Record<string, any>;  // aliases, parent_location 等
}
```

### 3.2 存储隔离

- 优先每个剧本独立 namespace / partition
- 若共享 collection，`script_id + script_version` 过滤为强制
- 封装 `search(roomId, query)` 服务，业务层不得直接访问向量库

### 3.3 检索流程

1. 读取房间的 `script_id + script_version + current_scene + 当前剧透等级`
2. **先硬过滤，后向量相似度**：
   ```
   script_id = 当前剧本
   AND script_version = 当前房间版本
   AND (scene_id = 当前场景 OR scene_id IS NULL)
   AND spoiler_level <= 当前进度
   ```
3. 向量检索 topK
4. （可选）BM25 补充专有名词
5. （可选）RRF 融合 + reranker 重排
6. 返回 top 3~5 压缩卡片

---

## 4. 异步任务与进度

- 上传后创建 `ImportJob`，状态：`pending / parsing / chunking / extracting / merging / carding / summarizing / embedding / done / failed`
- 后台队列异步执行，各阶段更新进度百分比
- 前端实时显示进度（推荐 SSE 或 WebSocket；若前端栈不便，轮询也可）
- 每阶段输出中间 JSON，便于调试与人工抽检
- 失败可重试指定阶段，不必从头跑

建议数据模型：

```typescript
interface ImportJob {
  id: string;
  scriptId: string;
  targetVersion: string;
  sourceFileUrl: string;
  status: string;
  progress: number;           // 0~100
  currentStage: string;
  stageProgress: number;      // 当前阶段内的百分比，如 12/50 块
  stageMeta: {                // 各阶段计数，用于 UI 显示
    totalChunks?: number;
    processedChunks?: number;
    totalCards?: number;
  };
  error?: string;
  intermediateResults: {
    parsedText?: string;
    chunks?: any[];
    extractions?: any[];
    merged?: any;
    cards?: any[];
    summary?: string;
  };
  createdAt: Date;
  updatedAt: Date;
}
```

---

## 5. UI 需求（本次新增重点）

请先阅读现有前端技术栈与 UI 组件库，沿用其风格与组件。

### 5.1 入口

- 在已有的导入剧本模块新建
- 支持拖拽上传 + 点击选择文件
- 支持格式：`.docx`、`.pdf`、`.txt`、`.md`
- 上传前可填写：剧本名称、简介、是否公开

### 5.2 上传与解析进度

- 上传时显示文件上传进度条
- 上传完成后切换到“处理进度”视图
- 显示当前阶段名称（解析文档 / 章节切分 / 结构化抽取 / 合并 / 卡片生成 / 总纲生成 / 向量入库）
- 显示总进度条 + 阶段内进度（如“结构化抽取 12/50”）
- 显示预计剩余时间（可选）
- 支持刷新页面后继续看到进度（进度数据存后端，不依赖前端内存）
- 失败时显示错误信息 + “重试该阶段”按钮

### 5.3 完成后预览与审核

处理完成后，进入预览审核页：

- **总览卡片**：显示生成的剧本名称、版本、卡片统计（地点 / NPC / 事件 / 线索 / 场景数量）
- **总纲预览**：显示生成的全局总纲，可编辑
- **卡片列表**：按类型分组（地点 / NPC / 事件 / 线索 / 规则 / 分支 / 结局），支持：
  - 按类型、剧透等级筛选
  - 搜索
  - 编辑卡片内容与元数据
  - 合并、拆分、删除卡片
  - 冲突条目高亮提示
- **来源追溯**：每张卡可查看 `source_quote` 与原文位置，便于校对
- 顶部提供“重新生成某类卡片”（可选，针对某阶段单独重跑）
- 底部提供“发布”与“取消”

### 5.4 发布

- 点击“发布”后，生成正式 `script_version`，状态变为 `published`
- 发布后跳转到剧本详情页，可直接开房间
- 支持“跳过审核直接发布”（风险自负，需二次确认）
- 支持查看历史版本与回滚（至少保留列表）

### 5.5 错误与边界状态

- 文件格式不支持：明确提示
- 文件过大：显示上限并拒绝
- 解析失败：展示原因与建议
- LLM 抽取失败：可单独重试该块或该阶段
- 任务超时：可重新触发
- 前端断线重连后：进度自动恢复显示

### 5.6 交互细节

- 所有长任务必须有 loading 态，禁止界面卡死
- 进度条更新平滑，避免频繁抖动
- 阶段切换有明确视觉反馈（如阶段列表高亮当前阶段）
- 关键操作（发布、删除、合并）需二次确认
- 卡片编辑后本地保存草稿，防丢失

如果项目暂时不做复杂界面，**至少实现**：上传入口 + 实时进度条 + 完成后卡片列表预览 + 发布按钮。其余可留 TODO 并记录。

---

## 6. API 设计（至少包含）

**导入相关**：
- `POST /scripts/import` 上传文件，创建导入任务，返回 `jobId`
- `GET /scripts/import/:jobId` 查询进度、阶段、中间结果摘要
- `GET /scripts/import/:jobId/stream` SSE 推送进度（或 WebSocket 端点）
- `POST /scripts/import/:jobId/retry` 重试指定阶段
- `POST /scripts/import/:jobId/cancel` 取消任务

**卡片与版本**：
- `GET /scripts/:id/versions` 版本列表
- `POST /scripts/:id/publish` 从预览版本正式发布
- `GET /scripts/:id/cards` 查看卡片（支持按 type / scene / spoiler 过滤）
- `PUT /scripts/:id/cards/:cardId` 编辑卡片
- `POST /scripts/:id/cards/merge` 合并卡片
- `POST /scripts/:id/cards/:cardId/split` 拆分卡片
- `DELETE /scripts/:id/cards/:cardId` 删除卡片
- `POST /scripts/:id/search` 内部检索（或封装为服务）

**房间对接**：
- 创建房间时绑定 `script_id + version`

---

## 7. 目录结构建议

请对齐现有目录风格，不要另起一套。

---

## 8. 落地步骤建议

1. **先阅读现有代码**：房间绑定方式、剧本分块实现、数据模型、LLM 调用方式、前端框架与 UI 组件库。
2. **输出改造计划**：哪些复用、哪些扩展、哪些新建，写入 README 或单独文档。
3. **先做后端离线脚本**：跑通“解析 → 切分 → 抽取 → 合并 → 卡片化 → 总纲 → 入库”。
4. **再接异步任务与 API**，实现进度查询。
5. **再做前端上传 + 进度页**，用 SSE 或轮询。
6. **然后做审核页与发布流程**。
7. **最后与已有房间系统对接**，验证新房间能正常玩。

---

## 9. 测试与验收

**后端**：
- 导入测试：5 万字 Word + PDF，跑通全流程
- 防串测试：两个相似剧本交叉提问，top-k 不含其他 `script_id`
- 防剧透测试：未解锁线索不被检索
- 缓存命中测试：同剧本同场景多轮，前缀缓存命中率 > 80%
- token 对比：全量 vs 按需，输入 token 下降 > 60%
- 版本测试：导入生成新版本，旧房间不受影响
- 失败重试测试：抽取阶段失败可单独重试

**前端**：
- 上传交互：拖拽、点击、格式校验、大小限制
- 进度展示：阶段切换正确、百分比准确、刷新后恢复
- 断线重连：SSE/WS 断开后自动重连或降级轮询
- 审核交互：编辑、合并、拆分、删除、冲突高亮
- 发布流程：二次确认、发布成功跳转
- 错误状态：解析失败、抽取失败、超时都有明确提示与恢复入口

---

## 10. 交付要求

- **不重写已有可用模块**，优先兼容改造；冲突处记录原因
- 代码类型安全、模块解耦、可测试
- README 包含：技术选型理由、架构图、环境变量、启动方式、API 文档、迁移说明、示例剧本与房间数据
- 保留原始文档与中间结果，便于后续增量更新
- 遇到规格未覆盖处，做合理假设并记录


---

请开始实现。