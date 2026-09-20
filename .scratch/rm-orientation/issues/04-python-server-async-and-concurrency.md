# 04 - Python 异步服务端并发状态与业务全量补齐

Type: prototype
Status: open
Blocked by: 03

## Question

在 `projects/python/server-async/` 中，如何实现完整的文本 CRUD、注销级联清理、`--token-ttl-seconds` 命令行解析与无续期到期判定，并将密码计算剥离事件循环，确保在并发同名注册竞争和旧账号登录挂起并注销重注册时保持数据严格一致与隔离？
