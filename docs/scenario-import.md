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

导入较长文档时，服务端会先在本地识别章节边界，再按最多 8 个章节或约 24000 字分轮
请求 AI；每轮都保留原文，任一轮超时都会回退到本地结构化结果。导入弹窗会显示预计
请求轮数并询问是否启用 AI。相关配置位于 `data/config/general.toml`：

```toml
[scenario_import]
timeout = 300
stream_output = true
```

运行时通过精简房间快照、只注入最近历史、摘要与正文分离来降低输入 token；不对 KP
单轮输出设置人为上限。模块摘要接口使用低温度并按需调用，避免每轮重复发送长文本。
