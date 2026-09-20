# RM 软件组招新考核领域术语模型 (Domain Model)

本文档定义本项目核心业务与工程领域的权威术语与概念边界，确保在设计、代码实现与面试答辩中使用统一、精确的概念。

---

## 核心领域概念 (Glossary)

### 1. 考核与路线 (Tracks & Tiers)
* **候选人 (Candidate)**: 参加 RM 软件组考核的学生开发人员。
* **路线 (Track)**: 项目技术实现路线，分为 **Python 路线**（FastAPI / Uvicorn / pytest）与 **Rust 路线**（Rocket / Tokio / Cargo）。两条路线遵循完全等价的协议与验收标准。
* **层级 (Tier)**:
  * **同步客户端 (`client-sync`)**: 交互式命令行 HTTP 客户端，必做。负责命令循环、多行输入、Token 本地缓存与清理、网络失败容错。
  * **同步服务端 (`server-sync`)**: 同步业务服务端，可选过渡层。用于学习在同步接口下保护共享状态。
  * **异步服务端 (`server-async`)**: 异步并发服务端，必做。负责高并发 HTTP 处理、事件循环保护与耗时任务剥离。
* **参考程序 (Reference Programs)**: 官方编译发布的标准二进制程序（`rm-client-sync` 与 `rm-server-async`），作为与候选人代码进行黑盒交叉验证的基准。

### 2. 用户与会话鉴权 (User & Session Authentication)
* **用户名 (Username)**: 1–32 个 ASCII 字母、数字、下划线或连字符，区分大小写。全局唯一。
* **密码 (Password)**: 8–128 个 Unicode 标量值 (Unicode Scalar Values)。计算长度时不以 UTF-8 字节或复合字形（Grapheme Clusters）为单位。
* **密码哈希与阻塞剥离 (Password Hashing & Blocking Isolation)**: 密码哈希（如 Argon2 / PBKDF2）属于 CPU 密集型计算。在异步服务端中，严禁在异步事件循环线程上直接执行，必须剥离至专用阻塞线程池（如 Tokio `spawn_blocking` 或 Python 线程池）。
* **会话令牌 (Session Token)**: 成功登录后服务端颁发的 Bearer 凭据。每个用户在系统中**至多只有一个有效令牌**。
* **令牌过期与无续期机制 (Token TTL & Non-sliding Expiry)**: 服务端通过 `--token-ttl-seconds` 启动参数指定固定有效期（默认 300 秒）。成功登录时响应 `expires_in`。任何操作**均不延长/续期**有效时间，到期后立即失效返回 401。
* **令牌失效场景**:
  1. 超过 TTL 固定有效期；
  2. 用户再次登录（生成新令牌并强制使旧令牌失效）；
  3. 用户调用 `DELETE /sessions/current` 主动退出；
  4. 用户注销账号。

### 3. 数据隔离与生命周期 (Data Isolation & Lifecycle)
* **文本对象 (Text Entity)**: 每个用户独立命名空间的文本记录。名称由 1–64 个 ASCII 字符组成，内容 UTF-8 编码上限为 65,536 字节。
* **租户隔离 (Tenant Isolation)**: 不同用户可以拥有完全相同名称的文本，但相互绝对不可见、不可改、不可删。
* **账号注销级联清理 (Cascade Deletion on Deregistration)**: `DELETE /users/me` 执行时，必须以原子/一致性方式同时清理当前用户、该用户的全部有效令牌以及名下的所有文本对象。
* **注销与登录竞争隔离 (Deregistration-Login Race Immunity)**: 若旧账号的登录正在并发哈希计算中，此时该账号被注销并被同名重新注册，已发起的旧登录操作必须被判定无效，绝不能作用或附加到新注册的同名账号上。

### 4. 并发一致性与网络锁约束 (Concurrency & Lock Invariants)
* **内存状态 (In-Memory State)**: 服务端所有数据存储于单进程内存中，无需持久化到磁盘。
* **读写锁分离 (RwLock / Mutex Protection)**: 内存数据结构通过并发锁保护。多读者并发读取文本，写操作（注册、覆盖、删除、登录、注销）互斥。
* **无网络等待锁守则 (No Await Under Lock)**: 在持有读锁或写锁的任何临界区内，**绝对禁止**进行任何网络 I/O、HTTP 响应发送或跨上下文 `await`，避免造成工作线程饥饿或并发死锁。

### 5. 交付与面试防御 (Deliverables & Defense)
* **自然提交历史 (Natural Git History)**: 遵循语义化、小步演进的 Commit 提交历史，清晰展示功能实现、重构与测试验证过程。
* **面试白皮书 (Interview Defense Notes)**: 针对底层内存模型、并发竞争防御、事件循环原理以及 Python vs Rust 架构对比形成的深度答辩知识体系。
