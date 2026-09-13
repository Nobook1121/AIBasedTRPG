# AI Runtime Improvements Design

## Goal

在保留现有剧本模块、房间工具和角色配置行为的前提下，降低每轮 AI 请求的动态输入量，稳定共享提示词前缀，并补齐小模型分流、结构化输出、缓存可观测性和每日 token 看板。

## Scope and compatibility

- 继续使用 Flask、JSON 文件运行时存储和现有 OpenAI-compatible provider 接口，不强制引入 Redis 或新的数据库依赖。
- 旧房间 `info.json`、`messages.json`、历史文件和旧的非 JSON KP 回复继续可读。
- AI 仍不能直接改变房间状态；状态更新由后端白名单校验后执行。
- 现有剧本模块工具、场景切换权限和角色工具白名单保持兼容。

## Architecture

### Prompt layers

每轮请求使用固定顺序：

1. 全局系统规则（固定文本）；
2. 剧本静态核心（剧本 ID/版本）；
3. 场景静态卡（场景 ID/版本，最多注入当前相关模块）；
4. 房间动态状态投影；
5. 滚动摘要、结构化事件日志和最近原文；
6. 当前玩家输入。

静态层由稳定版本计算，不包含房间 ID、用户名、时间戳或随机数。构建器输出 `messages` 和 `cache_key`，供请求、日志和前端指标复用。

### Externalized room state

每个房间增加 `state.json`，字段包含 `active_scene_id`、`triggered_event_ids`、`clues`、`npc_attitudes`、`items`、`quests`、`timeline`、`rolling_summary` 和 `event_log`。缺失时从 `info.json` 和最近消息推导空默认值，不阻塞旧房间。

### Small-model routing

平台配置增加可选 `small_models` 与 `tasks`。任务名采用可扩展映射：`intent_classification`、`state_update`、`summarization`、`schema_repair`。百炼、DeepSeek、OpenAI 配置提供默认小模型条目；未配置或调用失败时使用规则代码和现有大模型兼容路径。

### Structured output

KP 请求优先要求 JSON 对象：`narration`、`options`、`state_updates`、`next_scene`、`npc_actions`。后端执行严格 schema 清洗：未知字段丢弃，状态更新仅允许白名单字段，场景只能切换到当前剧本 manifest 中存在的节点。无法解析时保留原始文本，不重复请求大模型。

### Cache and telemetry

缓存元数据使用确定性键：`scenario:{scenario_id}@{scenario_version}:scene:{scene_id}@{scene_version}:rules:{rules_version}`，不包含房间 ID。实现内存/文件可替换的 provider prefix、精确缓存和状态绑定语义缓存接口；当前只需记录命中情况，不改变 provider 请求协议。

每次 AI 调用记录角色、provider、model、输入 token、输出 token、总 token、缓存命中 token、缓存命中率、耗时、房间和场景。统计按日期和 `agent_id` 聚合，并提供设置 API。

## Frontend

- KP 消息 processing 区域显示耗时、token 和缓存命中率。
- 设置页新增每日 token 看板，按 AI 角色显示汇总，并保留未知/未来角色的动态行。
- 模型设置增加小模型任务配置展示/编辑入口，复用已有 provider 保存接口。

## Testing

新增单元测试覆盖 prompt 层顺序与稳定键、房间状态持久化、结构化输出校验、token/cache 统计聚合、配置默认值和前端展示契约；现有测试必须继续通过。
