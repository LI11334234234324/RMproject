# 06 - Rust 路线基础架构与核心语法要点研究

Type: research
Status: open
Blocked by: 01

## Question

针对 C/Python 背景的初学者，本项目 `projects/rust/` 所涉及的 Rocket、Tokio、Ureq、Serde 等核心依赖库的架构模式是什么？在实现 HTTP 服务与客户端时，Rust 的所有权移动、借用检查（`&` 与 `&mut`）、生命周期与智能指针（`Arc`, `Box`, `String` vs `&str`）有哪些常见陷阱与惯用法？
