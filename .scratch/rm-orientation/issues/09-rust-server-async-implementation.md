# 09 - Rust 异步服务端业务与并发隔离完整实现

Type: prototype
Status: open
Blocked by: 07, 08

## Question

在 `projects/rust/server-async/` 中，如何基于 Rocket 实现 Bearer Token 鉴权请求守卫（FromRequest Request Guard），将 CPU 密集型密码哈希计算剥离至 `tokio::task::spawn_blocking`，并落地完整的参数边界、Token TTL 与并发注销隔离？
