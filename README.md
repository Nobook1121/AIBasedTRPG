# AIBasedTRPG

AIBasedTRPG 是一个基于 Flask 后端与静态 HTML/CSS/JavaScript 前端的 AI TRPG 跑团辅助工具。当前架构保留原有页面、接口路径、JSON 数据格式和全局前端函数，并逐步拆分为更容易测试和维护的模块。

## 环境准备

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

本项目还需要本机可用的 `node`，用于从 TypeScript 源码构建浏览器运行脚本。

## 启动

从 GitHub 克隆源码后，先安装依赖并构建前端：

```powershell
npm install
npm run build:frontend
```

然后启动后端服务：

```powershell
python server.py
```

服务默认读取 `data/config/network.json` 中的端口配置，未配置时使用 `8086`。也可以通过命令行传入端口：

```powershell
python server.py 8090
```

如果目标端口已被占用，服务会尝试寻找附近可用端口，并在日志中输出监听地址，例如 `listening on http://127.0.0.1:8086`、局域网地址和 ZeroTier/Tailscale 等虚拟网卡地址。

## 验证

每次重构或提交前运行：

```powershell
.\scripts\verify.ps1
```

验证脚本会执行 Python 编译检查、TypeScript typecheck/build、关键 JavaScript 文件 `node --check` 和 `pytest -q`。

## 关键目录

- `backend/trpg_server/`：Flask app factory、蓝图路由、Socket.IO 事件、日志、安全与 JSON 存储工具。
- `tests/`：后端单元测试和 API smoke tests。
- `frontend/src/app/`：浏览器全局脚本的 TypeScript 业务源码，构建后仍按 `/js/...` URL 加载。
- `frontend/src/types/`：跨前端模块复用的手写类型声明。
- `frontend/src/react/`、`frontend/src/styles/`、`frontend/src/templates/`、`frontend/src/tools/`：React island、全局样式、HTML 模板和前端工具源码。
- `dist/public/`：统一的前端构建产物目录，默认不提交到 Git；浏览器运行时仍使用 `/js/...` 和 `/data/tools/...` URL。
- `data/config/`：TOML、JSON、角色提示词等运行配置数据。
- `data/scenarios/`：剧本 JSON 数据。
- `data/runtime/rooms/`：房间、房间消息、回档节点和自动存档数据。
- `data/runtime/users/`：用户数据与用户 IP 配置。
- `data/runtime/characters/`：角色卡运行数据；浏览器本地创建的角色卡仍保存在当前浏览器 `localStorage`。
- `data/assets/avatars/`、`data/assets/scenario_covers/`、`data/assets/aiplatform/` 与 `data/assets/vendor/`：上传头像、剧本封面、AI 平台图标和本地第三方静态资源。
- `data/runtime/logs/`：运行日志输出目录，运行时自动创建；默认只记录登录、消息、AI 请求和报错等关键事件。

## 配置与安全

生产或长期运行环境应设置 `AI_TRPG_SECRET_KEY`，避免使用默认开发密钥：

```powershell
$env:AI_TRPG_SECRET_KEY = "change-me"
```

涉及用户输入路径的后端代码应使用 `trpg_server.security.safe_join`；写入 JSON 应使用 `trpg_server.json_store.write_json_atomic`，避免路径穿越和半写入文件。源码位于 `backend/trpg_server/`，根目录 `server.py` 会兼容导入该包。

同一账号只允许一个有效会话。新的登录会使该账号旧会话失效，旧会话再次访问 API 时会收到 `401 Session expired`。

### Cookie 与登录状态

- 后端使用 HttpOnly Flask session cookie 保存登录会话，前端不会把密码、session token 或可冒充身份的数据写入 cookie。
- 首次访问页面会询问是否同意可选 cookie。拒绝时仍可登录和使用必要会话 cookie，但不会记录上次用户名和上次房间偏好。
- 可选 cookie 仅保存 `trpg_last_username`、用户级上次房间等本地偏好。
- session cookie 默认 `HttpOnly`、`SameSite=Lax`，登录后默认保留 7 天；同一账号在新设备登录会使旧会话失效。

### 用户管理

- 用户名要求 3-32 个字符，可包含字母、数字、下划线、点和连字符。
- 密码至少 8 个字符。
- 邮箱必须符合基本邮箱格式。
- 用户名按大小写不敏感方式查重，防止 `Alice` 和 `alice` 被注册为两个账号。
- 个人资料更新会复用同一套用户名和邮箱校验。

## 房间与回档

- 玩家登录后可以创建房间，创建时需要填写房间名并选择剧本。
- 普通 `USER` 默认最多创建 3 个房间；`ADMIN` 和 `OWNER` 可创建任意数量房间，并可加入任意房间旁观。
- 房间创建后会生成唯一房间码，其他玩家通过房间码加入。
- 玩家进入房间后，主页聊天记录会切换为该房间的持久聊天记录；消息保存发送者 ID、用户名和头像，重新进入房间后展示保持一致。
- 原独立存档系统已并入房间。房间内的“回档节点”会保存当前全部聊天内容，之后可恢复到该节点。
- 启用自动保存后，程序按常规设置中的自动保存间隔保存当前房间消息。
- 创建房间、加入房间、房间消息、回档节点等关键房间操作会写入日志。

## 部署与访问

### 本地单机运行

```powershell
python server.py
```

浏览器访问：

```text
http://127.0.0.1:8086
```

如果传入端口：

```powershell
python server.py 8090
```

则访问：

```text
http://127.0.0.1:8090
```

### 局域网访问

主机启动服务后，局域网内好友访问主机 IP 和端口，例如：

```text
http://192.168.1.23:8086
```

主机需要允许防火墙放行对应端口。好友访问后应注册/登录自己的账号。涉及写入主机文件的操作，例如上传头像、创建剧本、上传剧本封面、编辑或删除剧本，都由后端进行 session、owner/admin 权限、文件名、路径和大小校验。

### 内网穿透或异地组网

本程序不内置内网穿透、异地组网、端口映射或公网代理能力。用户可以自行使用 frp、ZeroTier、Tailscale、WireGuard、路由器端口映射或其他工具，把主机地址暴露给好友。

使用 ZeroTier、Tailscale 或 WireGuard 这类异地组网时，好友应访问主机在虚拟网卡上的 IP，而不是主机物理局域网 IP。主机启动日志会列出多个 `listening on http://<ip>:<port>` 地址；如果电脑的 ZeroTier 地址是 `192.168.192.31`，端口是 `8086`，手机应访问：

```text
http://192.168.192.31:8086
```

如果访问超时，优先检查：

- ZeroTier Central 中电脑和手机是否都已 `Authorized`。
- 手机 ZeroTier 客户端是否已连接同一个网络。
- Windows 防火墙是否允许 Python 或本程序端口对 ZeroTier 网络入站访问。
- 手机是否能 ping 通主机 ZeroTier IP，或能访问同网段其他服务。
- 启动日志是否包含对应端口的 `listening on http://<ZeroTier IP>:<port>`。

无论使用哪种网络方式，都建议：

- 使用强 `AI_TRPG_SECRET_KEY`。
- 为每个好友创建独立账号，不共享账号。
- 不把管理账号给普通玩家使用。
- 仅暴露本程序端口，不暴露项目目录、远程桌面或系统管理端口。
- 定期备份 `data/`。其中包含运行配置、剧本、上传头像、剧本封面，以及 `data/runtime/` 下的房间、用户、聊天历史和日志。

联机访问本程序时，页面和 REST API 使用 HTTP；实时聊天同步使用 Socket.IO，底层由 Engine.IO 管理，优先使用 WebSocket，必要时回退到 HTTP long-polling。ZeroTier 只提供虚拟网络通道，本程序本身不实现 ZeroTier 协议。若部署在反向代理和 HTTPS 后面，对外访问会变为 HTTPS，实时通道对应为 WSS。

### 云服务器部署

云服务器上可以直接运行：

```powershell
python server.py 8086
```

也可以在 Linux 上使用同等命令：

```bash
python server.py 8086
```

生产环境建议放在 Nginx、Caddy 或其他反向代理后面，由反向代理负责 HTTPS、域名和访问日志。本程序仍监听内网端口，例如 `127.0.0.1:8086` 或服务器内网地址。

反向代理需要转发 WebSocket，因为聊天同步使用 Socket.IO。Nginx 示例：

```nginx
location / {
    proxy_pass http://127.0.0.1:8086;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### 前端开发构建

`dist/public/` 是构建产物，源码仓库默认不提交该目录。首次克隆、拉取前端源码更新，或修改 TypeScript 源码后运行：

```powershell
npm install
npm run typecheck
npm run build:frontend
```

生成的浏览器文件统一输出到 `dist/public/`，其中包含页面、`js/` 和 `data/tools/`。未构建前端时，`python server.py` 可以启动后端，但浏览器页面会缺少页面或脚本而无法正常使用。

## 进一步文档

- [API Overview](docs/api.md)
- [Development Notes](docs/development.md)

## AI 剧本检索与版本隔离

当前 AI 运行时使用兼容式的知识卡片检索链：剧本模块会被规范化为带有
`scenario_id`、`scenario_version`、`scene_id`、`card_type`、`visibility`、
`spoiler_level`、`unlock_condition` 和 `text` 的卡片。聊天请求通过
`KnowledgeBaseService.search(room_id, query)` 访问检索服务；服务先按房间绑定的剧本、
版本、当前场景和剧透等级过滤，再进行确定性的词法排序，因此业务层不会直接访问索引。
默认实现不新增向量数据库依赖，后续可用相同卡片接口替换为 Chroma、pgvector 或远程向量服务。

剧本记录使用永久 `id` 与发布递增的 `scenario_version`。创建房间时会把当前版本写入
`info.json`，旧房间继续锁定原版本；编辑剧本会生成下一版本，新房间默认使用最新版本。
所有 Prompt 缓存键、知识库过滤和房间快照都携带版本号。迁移到新版本应由上层提供实体映射，
并通过 `validate_version_migration` 校验场景、NPC、线索和道具是否仍可对应。

架构边界：

```text
房间请求 -> 版本绑定加载 -> 知识卡片过滤/排序 -> 分层 Prompt -> LLM
    |              |                  |                  |
 state.json   scenario.json     versions/<n>.json    JSON 校验/状态更新
```

版本相关 API：

- `POST /api/rooms/<room_id>/scenario-migration`：提交 `scenario_version`、实体 `mapping`，迁移前校验映射，失败时不写入房间。
- `POST /api/scenarios/<scenario_id>/archive`：归档剧本版本；有房间引用时删除接口也只归档，不物理删除。
- `DELETE /api/scenarios/<scenario_id>`：无房间引用时删除，存在引用时自动转为归档。

缓存层：provider 前缀缓存用于稳定 Prompt 前缀；无房间请求使用带剧本版本、场景、状态摘要和输入哈希的精确缓存；房间请求使用包含 `room_id`、剧本版本和状态的语义缓存，避免房间间复用。缓存均为进程内 TTL 缓存，重启后清空。

Telemetry 观测：

1. 确保账号拥有 `settings.ai_models` 权限。
2. 打开设置页的 AI Token Dashboard，或请求 `GET /api/telemetry/ai/daily`；可选 `?day=YYYY-MM-DD` 查询历史日期。
3. 后端原始记录位于 `data/runtime/logs/ai_usage.jsonl`。每条记录包含 `prompt_tokens`、`completion_tokens`、`cached_tokens`、`cache_hit_rate`、`prefix_cache_hit`、`scenario_id`、`scenario_version`、`scene_id`、`room_id` 和 `elapsed_ms`。
4. API 返回 `prefix_cache_hit_rate`、`scenario_distribution` 和 `room_costs`，分别用于前缀命中率、剧本串扰分布和房间 token 成本观测。真实 Provider 是否命中其服务端前缀缓存，以返回的 `cached_tokens` 为准；本地 `prefix_cache_hit` 只表示稳定前缀键已被复用。

建议验收方式：同一剧本/场景连续发送至少 20 轮后，检查 `prefix_cache_hit_rate > 80`；对比全量注入和按需检索两组请求的 `prompt_tokens`，计算输入 token 降幅；若 `scenario_distribution` 出现非当前剧本 ID，应立即检查房间版本绑定和检索过滤。

示例房间绑定：

```json
{"id":"room-1","scenario_id":7,"scenario_version":"3","active_scene_id":"scene-1"}
```

示例迁移请求：

```json
{"scenario_version":"4","mapping":{"scene-1":"scene-a","npc-1":"npc-a"},"old_entities":[{"id":"scene-1"},{"id":"npc-1"}]}
```

结构化 KP 输出只能更新白名单字段，且 `next_scene`、NPC、线索和道具必须存在当前剧本版本的
索引中；非法实体会被丢弃，不会触发自动重试。房间状态通过 `project_room_state` 投影为当前场景、
有限事件日志和滚动摘要，完整历史仍保存在房间运行数据中。
### External ruleset knowledge bases

Administrators can use the settings page's Ruleset Knowledge Base tab to upload `.txt`, `.md`, `.doc`, or `.docx` files for COC7. The service extracts headings, rule topics, formulas, tables, exceptions, and examples into semantic chunks; this chunker is deliberately separate from scenario scene/module chunking. Versioned indexes are stored under `data/runtime/knowledge-bases/` and room bindings keep `ruleset_id` plus `knowledge_version`.

The protected API requires `settings.knowledge_bases`:

- `GET /api/knowledge-bases/rulesets`
- `POST /api/knowledge-bases/<ruleset_id>/sources`
- `POST /api/knowledge-bases/<ruleset_id>/reindex`
- `POST /api/knowledge-bases/<ruleset_id>/enable` or `/archive`
- `POST /api/rooms/<room_id>/rulesets`

Index failures retain the previous active version. Future COC6 or D&D adapters can implement the same `RulesetAdapter` interface and reuse upload, versioning, permissions, retrieval, prompt, and telemetry infrastructure.
