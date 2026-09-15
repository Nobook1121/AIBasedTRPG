# 剧本导入与低 token 运行方式

`scripts/convert_scenario.py` 支持 `.txt`、`.md` 和 `.docx`：

```powershell
python scripts/convert_scenario.py docs/样本/模组.docx -o scenario.json --title "我的剧本"
```

输出 JSON 可在剧本编辑器中导入，或提交到 `POST /api/scenarios`。网页端也可调用
`POST /api/scenarios/import`（JSON `{ "text": "...", "title": "..." }` 或 multipart
字段 `file`）先预览转换结果，再决定是否保存。

转换器把原文拆成有序模块，并为每个模块生成短摘要；`content` 永远保留原文，摘要
不作为事实来源。场景/结局会获得稳定 ID，便于 KP 确定性转场。

运行时房间快照仅发送剧本身份、当前场景 ID 和场景清单摘要。KP 需要叙事细节时才调用
`room.get_scenario_module`；明确转场时调用 `room.activate_scenario_scene`，且 ID 必须来自
清单。房间创建时自动锁定第一个场景，后续状态写入 `info.json`。因此不会因摘要遗漏而
凭空产生“驾驶室”等剧本外设施。

运行时通过精简房间快照、只注入最近历史、摘要与正文分离来降低输入 token；不对 KP
单轮输出设置人为上限。模块摘要接口使用低温度并按需调用，避免每轮重复发送长文本。
# 异步剧本导入

剧本文档可通过 `POST /api/scripts/import` 上传 `.docx`、`.pdf`、`.txt` 或 `.md`。任务状态保存在
`data/runtime/scenario_imports/<job_id>/job.json`，原始文件和中间结果位于同一任务目录；使用
`GET /api/scripts/import/<job_id>` 查询，或连接 `/stream` 获取 SSE 进度。失败任务可调用
`POST .../retry`，运行中任务可调用 `POST .../cancel`。

完成后，审核内容通过 `PUT .../<job_id>/preview` 保存，并调用 `POST /api/scripts/<script_id>/publish`
发布。正式剧本位于 `data/scenarios/scenario-<id>/scenario.json`，版本快照位于
`versions/<version>.json`，知识索引（embedding 或词法兜底）位于 `knowledge-index/<version>.json`。
旧房间继续使用创建时绑定的版本；只有显式迁移接口会改变绑定。扫描 PDF 当前会提示需要 OCR，
不会丢弃原始文件。

启用 OCR：安装 `requirements-ocr.txt` 并设置 `AI_TRPG_OCR_ENABLED=1`。启用本地向量库：安装
`requirements-vector.txt`，执行 `docker compose -f docker-compose.qdrant.yml up -d`；Qdrant 数据位于
`data/runtime/vector-db/qdrant/`。Embedding 使用 `AI_TRPG_EMBEDDING_BASE_URL`、
`AI_TRPG_EMBEDDING_API_KEY`、`AI_TRPG_EMBEDDING_MODEL` 配置，失败时保留 JSON 索引并使用本地哈希向量。
