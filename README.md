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

- `trpg_server/`：Flask app factory、蓝图路由、Socket.IO 事件、日志、安全与 JSON 存储工具。
- `tests/`：后端单元测试和 API smoke tests。
- `frontend/src/`：TypeScript 前端源码。
- `js/`：TypeScript 构建生成的浏览器运行脚本，默认不提交到 Git。
- `data/tools/`：前端小工具脚本构建产物。
- `data/config/`：TOML、JSON、角色提示词等运行配置数据。
- `data/scenarios/`：剧本 JSON 数据。
- `data/rooms/`：房间、房间消息、回档节点和自动存档数据。
- `data/users/`：用户数据与用户 IP 配置。
- `data/characters/`：角色卡示例等角色数据资源；浏览器本地创建的角色卡仍保存在当前浏览器 `localStorage`。
- `data/assets/avatars/`、`data/assets/scenario_covers/` 与 `data/assets/aiplatform/`：上传头像、剧本封面和 AI 平台图标。
- `data/logs/`：运行日志输出目录，运行时自动创建；默认只记录登录、消息、AI 请求和报错等关键事件。

## 配置与安全

生产或长期运行环境应设置 `AI_TRPG_SECRET_KEY`，避免使用默认开发密钥：

```powershell
$env:AI_TRPG_SECRET_KEY = "change-me"
```

涉及用户输入路径的后端代码应使用 `trpg_server.security.safe_join`；写入 JSON 应使用 `trpg_server.json_store.write_json_atomic`，避免路径穿越和半写入文件。

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
- 定期备份 `data/`。其中包含运行配置、剧本、房间、用户、上传头像、剧本封面、聊天历史和日志。

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

`js/` 是构建产物，源码仓库默认不提交该目录。首次克隆、拉取前端源码更新，或修改 TypeScript 源码后运行：

```powershell
npm install
npm run typecheck
npm run build:frontend
```

生成的浏览器文件输出到 `frontend/dist/`、`js/`、`data/tools/` 路径。未构建前端时，`python server.py` 可以启动后端，但浏览器页面会缺少页面或脚本而无法正常使用。

## 进一步文档

- [API Overview](docs/api.md)
- [Development Notes](docs/development.md)
