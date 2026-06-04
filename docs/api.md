# API Overview

本文档记录当前 Flask 蓝图暴露的主要 HTTP API。除静态资源外，现有业务接口沿用 `success`、`message`、`data` 等既有响应字段。

## Pages And Assets

- `GET /`：返回主页面。
- `GET /<path:path>`：静态页面与资源回退。
- `GET /assets/avatars/<path:filename>`：读取用户头像。
- `GET /assets/scenario_covers/<path:filename>`：读取剧本封面。
- `GET /assets/aiplatform/<path:filename>`：读取 AI 平台图标。
- `GET /config/<path:filename>`：读取客户端配置文件。

## Scenarios

- `GET /api/scenarios`：列出剧本。
- `GET /api/scenarios/<scenario_id>`：读取单个剧本。
- `POST /api/scenarios`：创建剧本。
- `PUT /api/scenarios/<scenario_id>`：更新剧本。
- `DELETE /api/scenarios/<scenario_id>`：删除剧本。
- `POST /api/scenarios/cover`：上传剧本封面。
- `DELETE /api/scenarios/cover`：删除剧本封面。
- `POST /api/scenarios/cover/rename`：重命名剧本封面。
- `GET /api/scenarios/list`：列出剧本摘要。

## Auth And Users

- `POST /api/auth/register`：注册用户。
- `POST /api/auth/login`：登录用户。
- `POST /api/auth/logout`：退出登录。
- `GET /api/auth/status`：读取当前认证状态。
- `POST /api/auth/update`：更新当前用户资料。
- `GET /api/users`：列出用户。
- `PUT /api/users/<user_id>/role`：更新用户角色。
- `PUT /api/users/<user_id>/status`：更新用户状态。
- `GET /api/user/ip/config`：读取当前用户 IP 配置。
- `POST /api/user/ip/config`：保存当前用户 IP 配置。
- `GET /api/admin/ip/configs`：读取管理员可见的 IP 配置。

## Config

- `POST /api/config/<config_name>`：保存通用配置。
- `POST /api/config/aiplatform/<platform>`：保存 AI 平台配置。
- `POST /api/config/aiplatform/<platform>/test`：测试 AI 平台连接。
- `POST /api/config/aimodel/save`：保存 AI 模型配置脚本。
- `POST /api/config/aimodel/delete`：删除 AI 模型配置脚本。

## Chat

- `POST /api/chat`：向 AI 发送聊天请求。
- `POST /api/messages`：发送主页消息。
- `POST /api/scenarios/<script_id>/messages`：发送剧本消息。

## Network

- `GET /api/network/config`：读取网络配置。
- `POST /api/network/config`：保存网络配置。
- `GET /api/network/status`：读取网络状态。
- `POST /api/network/test`：测试网络连接。
- `GET /api/network/penetration/config`：读取穿透配置。
- `POST /api/network/penetration/config`：保存穿透配置。
- `GET /api/network/penetration/status`：读取穿透状态。

## Saves

- `GET /api/saves`：列出存档。
- `POST /api/saves`：创建存档。
- `DELETE /api/saves/<save_id>`：删除存档。
- `GET /api/saves/<save_id>/nodes`：列出存档节点。
- `POST /api/saves/<save_id>/nodes`：创建存档节点。
- `GET /api/saves/<save_id>/nodes/<node_filename>`：读取存档节点。
- `DELETE /api/saves/<save_id>/nodes/<node_filename>`：删除存档节点。
- `POST /api/saves/<save_id>/autosave`：写入自动存档。
- `GET /api/saves/<save_id>/autosave`：读取自动存档。

## Socket.IO Events

- `connect`：客户端连接。
- `disconnect`：客户端断开。
- `send_message`：广播实时消息。
- `typing`：广播输入状态。
