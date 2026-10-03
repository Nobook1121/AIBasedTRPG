# AIbased TRPG v0.4.2b

这是可用于 GitHub Release 的源码发布包，包含后端源码、前端源码、已构建的 `dist/public`、默认配置与运行脚本。

## 发布前检查

- `scripts/verify.ps1`：通过（Python 语法检查、前端 TypeScript 类型检查与生产构建、`node --check` 产物校验、`pytest` 292 passed）
- 发布包敏感信息扫描：不应包含本地 `.env`、运行时密钥、日志、缓存、本地数据库或依赖目录

## 启动

1. 安装 `requirements.txt` 中的 Python 依赖。
2. 如需重新构建前端，安装 Node.js 依赖后运行 `npm run build:frontend`。
3. 运行 `python server.py`。

AI 平台 API key 仅应通过运行时配置写入 `data/runtime/config/aiplatform/` 或环境变量提供，不要提交到 Git 或发布包。

## 本次更新

详见仓库 `release/changelog/v0.4.2b.md`。