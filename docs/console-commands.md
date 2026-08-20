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
