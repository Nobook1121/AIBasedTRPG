# Development Notes

## 架构边界

- `server.py` 只保留兼容启动入口和端口选择逻辑。
- `trpg_server.app_factory.create_app()` 负责创建 Flask app、初始化 CORS、Socket.IO、日志和蓝图。
- `trpg_server/routes/` 下每个文件只维护一个业务路由组。
- `trpg_server/socket_events.py` 维护 Socket.IO 事件注册。
- 前端仍使用静态 HTML、Bootstrap、原生 JavaScript 和全局初始化函数；迁移时必须保持现有 DOM id、接口路径和可见功能不变。

## 验证流程

提交前运行：

```powershell
.\scripts\verify.ps1
```

如果只改了单个前端文件，也要先运行对应文件的语法检查，例如：

```powershell
node --check js\tabs.js
```

当前测试在 Python 3.13 下会输出 Flask/Werkzeug 2.0.1 相关 `DeprecationWarning`。这些警告不是本轮验证失败条件，但属于后续兼容性治理项。

## 日志规范

- 使用 `logging.getLogger(__name__)` 或业务命名 logger。
- 请求日志由 `trpg_server.logging_config.register_request_logging` 统一记录 method、path、status、elapsed time、user id 和 client IP。
- 日志文件写入 `logs/ai_trpg.log`，使用 `RotatingFileHandler` 控制文件大小。
- 不要记录密码、API key、auth token、provider secret、上传文件内容或完整认证载荷。
- 需要输出字典前，优先使用 `trpg_server.logging_config.redact_sensitive`。

## 文件访问规范

- 请求参数参与路径拼接时，使用 `trpg_server.security.safe_join`。
- 上传文件扩展名校验使用 `trpg_server.security.is_allowed_upload`。
- JSON 读取使用 `trpg_server.json_store.read_json`。
- JSON 写入使用 `trpg_server.json_store.write_json_atomic`，避免进程中断时留下半写文件。

## 前端规范

- 新的接口调用优先使用 `js/api-client.js` 中的 `TrpgApi`。
- 新的 DOM 查询和事件绑定优先使用 `js/dom-utils.js` 中的 `TrpgDom`。
- 脚本只在 `index.html` 的 `</body>` 前加载，避免重复初始化。
- 交互状态需要同步可访问性属性，例如 `aria-expanded`、`aria-selected` 和 `aria-current`。
- UI 样式优先使用 `style.css` 顶部 token，避免继续散落硬编码颜色、阴影和圆角。
