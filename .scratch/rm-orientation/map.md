# Wayfinder Map: RM 软件组 2026 招新项目决胜地图

## Destination

在 2026 年 10 月 8 日前全面高质量攻克 RM 战队招新考核：以 Python 路线先验打通全协议闭环与测试基准，系统深度攻克 Rust 路线（交互式客户端、异步服务端与并发安全隔离），产出高质量交付物、双向交叉验收报告与《面试深度答辩白皮书》，具备在招新技术面试中对底层机制与架构决策进行降维答辩的绝对掌控力。

## Notes

- **领域上下文**：参见 [CONTEXT.md](../../CONTEXT.md)，严守统一术语、并发不变式与生命周期定义。
- **关联技能**：`grilling`, `domain-modeling`, `research`, `prototype`, `tdd`, `code-review`。
- **核心工程原则**：
  1. **小步提交**：严格维护自然清晰的 Git 提交历史，每个子任务或核心修复均有规范 commit。
  2. **双路验证**：Python 版与 Rust 版相互作为交叉对齐测试桩，结合官方参考程序形成三重断言。
  3. **面试穿透**：每步实现必须搞懂底层原因（为什么不用 Mutex、为什么不能 await 持锁、为什么必须 spawn_blocking、Rust 编译器在保证什么）。

## Decisions so far

<!-- the index: one line per closed ticket, enough to judge relevance, then zoom the link for the detail the ticket holds -->

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't ticket yet; graduates as the frontier advances -->

- 针对极限并发请求与大报文下的内存抖动及慢连接 DOS 防御机制。
- 若战队面试官提出将单进程内存状态无缝热迁移至持久化层或轻量级嵌入式存储（如 sled / redb）时的架构扩展方案。
- 模拟面试中针对极端考官提问风格（如深挖 CPU Cache Line 伪共享、Tokio 窃取式调度线程池细节）的应急话术与设计备忘。

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->

- 引入外置大型数据库（如 PostgreSQL/MySQL/Redis）—— 协议明确规定单进程内存存储。
- 跨节点分布式集群状态同步 —— 协议明确规定各实例独立持有数据。
- Web 前端界面或图形 GUI 开发 —— 项目目标纯粹为 CLI 交互式客户端与 HTTP 协议服务。
