# AIBasedTRPG

AIBasedTRPG 是一个基于 Flask 后端与静态 HTML/CSS/JavaScript 前端的 AI TRPG 跑团辅助工具。当前架构保留原有页面、接口路径、JSON 数据格式和全局前端函数，并逐步拆分为更容易测试和维护的模块。

## 环境准备

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

本项目还需要本机可用的 `node`，用于执行前端 JavaScript 语法检查。

## 启动

```powershell
python server.py
```

服务默认读取 `config/network.json` 中的端口配置，未配置时使用 `8086`。也可以通过命令行传入端口：

```powershell
python server.py 8090
```

如果目标端口已被占用，服务会尝试寻找附近可用端口，并在日志中输出局域网访问地址。

## 验证

每次重构或提交前运行：

```powershell
.\scripts\verify.ps1
```

验证脚本会执行 Python 编译检查、关键 JavaScript 文件 `node --check` 和 `pytest -q`。

## 关键目录

- `trpg_server/`：Flask app factory、蓝图路由、Socket.IO 事件、日志、安全与 JSON 存储工具。
- `tests/`：后端单元测试和 API smoke tests。
- `js/`、`tools/`、`config/`：前端脚本、工具和客户端配置加载逻辑。
- `scenarios/`：剧本 JSON 数据。
- `saves/`：存档、存档节点和自动存档数据。
- `users/`：用户数据与用户 IP 配置。
- `assets/`：头像、剧本封面和 AI 平台图标。
- `logs/`：运行日志输出目录，运行时自动创建。

## 配置与安全

生产或长期运行环境应设置 `AI_TRPG_SECRET_KEY`，避免使用默认开发密钥：

```powershell
$env:AI_TRPG_SECRET_KEY = "change-me"
```

涉及用户输入路径的后端代码应使用 `trpg_server.security.safe_join`；写入 JSON 应使用 `trpg_server.json_store.write_json_atomic`，避免路径穿越和半写入文件。

## 进一步文档

- [API Overview](docs/api.md)
- [Development Notes](docs/development.md)
