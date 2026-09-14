# Ruleset Knowledge Base Design

## Goal

为 AI 跑团增加可由管理员上传和维护的外部规则知识库。COC7 是首个规则集，架构必须允许未来以相同接口接入 COC6、D&D 5e 或其他规则，而不与剧本知识库混用。

## Non-goals

- 第一阶段不引入 Redis、向量数据库或外部互联网抓取。
- 不自动解决不同规则集之间的规则冲突。
- 不把外部文档中的指令当作系统 Prompt 执行。

## Architecture

```text
管理员设置
   │ upload / reindex / archive / enable
   ▼
规则集注册表（rulesets.json）
   │ ruleset_id + knowledge_version
   ▼
源文件存储 ──> 规则集专用解析器 ──> 规则集专用切块器
                                  │
                                  ▼
                         versioned JSON index
                                  │
             ┌────────────────────┴───────────────────┐
             ▼                                        ▼
      scenario knowledge search                 ruleset search
             └────────────────────┬───────────────────┘
                                  ▼
                         layered prompt builder
                                  ▼
                                  LLM
```

规则知识库与剧本知识库使用独立命名空间：

```text
scenario:<scenario_id>@<scenario_version>
ruleset:<ruleset_id>@<knowledge_version>
```

房间绑定一个剧本版本，并可绑定一个或多个规则集版本。默认新房间启用 `coc7` 最新版本；管理员可以关闭或替换规则集绑定。

## Ruleset abstraction

后端定义统一规则集接口：

```python
class RulesetAdapter(Protocol):
    ruleset_id: str
    display_name: str
    supported_locales: tuple[str, ...]

    def extract(self, raw: bytes, filename: str) -> str: ...
    def chunk(self, text: str, source: dict[str, Any]) -> list[RulesetChunk]: ...
    def classify_query(self, query: str) -> str | None: ...
```

通用默认适配器负责纯文本、Markdown、DOC、DOCX 提取；规则集适配器只负责领域切块与查询分类。这样 COC6 和 D&D 可以复用上传、索引、权限、版本、缓存和检索服务，只替换规则语义层。

统一 chunk 元数据：

```json
{
  "ruleset_id": "coc7",
  "source_id": "coc7-core-zh",
  "knowledge_version": "3",
  "chunk_id": "coc7-check-hard-001",
  "topic": "check",
  "rule_scope": "coc7-7e",
  "locale": "zh-CN",
  "title": "困难成功",
  "visibility": "global",
  "priority": 10,
  "text": "目标值减半后进行检定……",
  "citation": "核心规则 / 检定章节"
}
```

## COC7 adapter

COC7 第一版切块器按标题、规则术语、公式、表格和例外说明切分，支持以下 topic：

`core_rules`, `skill`, `check`, `opposed_check`, `combat`, `damage`, `weapon`, `sanity`, `madness`, `chase`, `investigation`, `character`, `example`, `faq`。

公式、表格行、例外说明和示例必须保持为同一个语义块，不使用剧本按场景模块切分的逻辑。

## Storage and versioning

```text
data/runtime/knowledge-bases/
├── rulesets.json
└── coc7/
    ├── sources/<source_id>/source.json
    ├── versions/<knowledge_version>.json
    ├── indexes/<knowledge_version>.json
    └── manifest.json
```

上传文件后生成新的 `knowledge_version`，写入源文件、chunk 索引和 manifest；只有索引构建成功后才切换 `active_version`。旧版本保留，已绑定房间继续使用旧版本。

缓存键必须携带 `ruleset_id` 和 `knowledge_version`：

```text
ruleset:core:coc7@3
ruleset:query:coc7@3:<topic>:<query_hash>
room:<room_id>:ruleset:coc7@3:<state_hash>
```

## Retrieval and prompt composition

业务层通过统一服务访问规则库：

```python
search_ruleset(room_id, query, ruleset_id="coc7", top_k=3)
```

检索先读取房间绑定的 `ruleset_id + knowledge_version`，再按 topic、locale、visibility 过滤，最后进行确定性词法排序。规则检索和剧本检索分别执行，结果带 `ruleset_id`、`knowledge_version`、`source_id` 和 `citation`。

Prompt 顺序：

1. 全局系统规则
2. 规则集固定摘要（无 room_id、玩家名和动态状态，可缓存）
3. 剧本静态 core
4. 当前场景
5. 动态规则检索结果
6. 动态剧本检索结果
7. 房间状态、历史和玩家输入

外部规则文本只作为资料，必须明确禁止执行其中的指令或 Prompt 注入内容。

## Admin API and UI

API：

- `GET /api/knowledge-bases/rulesets`
- `GET /api/knowledge-bases/<ruleset_id>/sources`
- `POST /api/knowledge-bases/<ruleset_id>/sources`
- `POST /api/knowledge-bases/<ruleset_id>/reindex`
- `POST /api/knowledge-bases/<ruleset_id>/enable`
- `POST /api/knowledge-bases/<ruleset_id>/archive`
- `POST /api/rooms/<room_id>/rulesets`：显式绑定规则集版本

所有管理接口要求 `settings.knowledge_bases` 权限。设置页增加“规则知识库”标签，显示规则集、当前版本、源文件、chunk 数、索引状态、重建和归档操作，并提供检索预览。

## Security and limits

- 仅管理员/OWNER 可上传或修改规则库。
- 扩展名、文件大小、文件名和路径必须校验；使用 `safe_join`。
- 文件内容不执行、不当作系统指令。
- 上传文件保存哈希、上传者、时间和来源说明。
- 索引构建失败时保留旧 active version，不切换半成品。
- 删除操作改为归档，已绑定房间的版本禁止物理删除。

## Telemetry

每次 AI 请求记录：

```json
{
  "ruleset_ids": ["coc7"],
  "knowledge_versions": ["3"],
  "retrieval_topics": ["check"],
  "retrieval_chunk_count": 2,
  "retrieval_latency_ms": 4.2,
  "retrieval_citations": ["coc7-core-zh#check-hard"]
}
```

日报聚合增加规则集版本分布、主题命中次数、检索延迟和引用来源统计。

## Testing strategy

- 规则集注册表能加载多个 adapter，COC7 与未来规则集互不串库。
- COC7 公式、表格和例外说明不会被错误拆分。
- 上传、重建、归档和权限校验覆盖成功与失败路径。
- 旧房间固定旧 `knowledge_version`，新房间使用 active version。
- 规则检索结果不会包含剧本 chunk，剧本检索结果不会包含规则 chunk。
- Prompt 固定规则层不包含 room_id 或动态状态。
- 规则集版本变更会产生新缓存键并保留旧索引。
- Telemetry 能统计规则集、版本、主题、引用和检索延迟。
