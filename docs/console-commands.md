# 控制台命令

服务器启动后，监听窗口会显示 `>` 提示符。网站管理员可以在该窗口输入站点管理命令。

## 语法

- 命令按空格分隔参数。
- 参数包含空格时使用英文双引号，例如 `"user name"`。
- 输入 `help` 查看当前可用命令。

## 用户权限

```text
user promote <username-or-id> [USER|ADMIN|OWNER]
```

将指定用户调整为目标权限。省略目标权限时默认提升为 `ADMIN`。

示例：

```text
user promote alice
user promote alice ADMIN
user promote 1 OWNER
```

## 安全退出

在服务器监听窗口输入以下任一命令即可请求安全关闭：

```text
shutdown
stop
server shutdown
```

命令通过仅允许本机访问、带随机令牌的内部接口触发 Flask-SocketIO 的停止钩子；
正在处理的请求会先完成，控制台命令线程随后退出。若服务尚未启动或接口不可达，
命令会返回错误而不会强制结束 Python 进程。
