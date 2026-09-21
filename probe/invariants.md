# 官方参考服务端四大并发与生命周期不变式实测报告

> 测试时间: 2026-09-21
> 测试目标: 官方参考程序 `rm-server-async.exe` (`reference-v0.2.0`, x86_64-pc-windows-msvc)
> 测试脚本: [`probe/invariants.py`](file:///C:/Users/16872/OneDrive%20-%20CUHK-Shenzhen/%E6%A1%8C%E9%9D%A2/AIspace/codex/rm%E9%A1%B9%E7%9B%AE/rmProject/probe/invariants.py)

---

## 一、测试结论汇总

| 不变式编号 | 不变式名称 | 协议规则核心点 | 实测判定 |
| :---: | :--- | :--- | :---: |
| **Invariant 1** | **固定 TTL 不续期**<br>*(Non-sliding Expiry)* | 会话令牌自签发开始计算固定有效期（如 2 秒）；期间发生的读取或写入请求**绝对不刷新/延长**过期时间。到期后首次请求立即返回 `401 Unauthorized` (`{"message":"Please log in again"}`)。 | ✅ PASS |
| **Invariant 2** | **租户完全隔离**<br>*(Tenant Isolation)* | 不同用户可以拥有完全相同名称的文本条目。各用户的文本命名空间相互独立，CRUD 操作互不可见、互不干扰。 | ✅ PASS |
| **Invariant 3** | **账号注销级联清理**<br>*(Cascade Deregistration)* | 调用 `DELETE /users/me` 成功后：① 原有效 Token 立即失效（401）；② 名下所有文本条目被彻底清空；③ 后续同名重新注册后，文本列表为空列表 `[]`，无任何历史数据残留。 | ✅ PASS |
| **Invariant 4** | **注销 × 登录竞争隔离**<br>*(Race Immunity)* | 当注销旧账号与登录旧账号并发交错执行时，由于旧账号已被级联销毁，旧凭据登录即便返回 Token 也会被标记销毁，或登录请求直接被拒绝（401），**绝无法附着或访问重新注册的同名新账号数据**。 | ✅ PASS |

---

## 二、实测过程详细记录

### 1. Invariant 1: 固定 TTL 不续期实测
- 服务端以 `--token-ttl-seconds 2` 参数启动。
- 注册用户 `alice` 并登录，获得初始 Token（有效期 2 秒）。
- 在 $t = 0.5\text{s}$ 时执行 `GET /texts`：正常响应 `200 OK`。
- 在 $t = 1.2\text{s}$ 时执行 `PUT /texts/k1` 写入操作：正常响应 `200 OK`。
- 在 $t = 2.3\text{s}$ 时（距登录 $2.3\text{s} > 2.0\text{s}$，但距上次写入仅 $1.1\text{s}$）执行 `GET /texts`：
  - **实测响应**：`401 Unauthorized`，Body: `{"message":"Please log in again"}`。
  - **结论**：证实官方服务端未采用滑动续期（Sliding Expiration），而是严格遵守自登录时刻起的硬过期（Hard Expiry）。

### 2. Invariant 2: 租户完全隔离实测
- 注册并登录两个不同用户：`alice` 与 `bob`。
- 两人分别创建同名笔记 `confidential`：
  - Alice 写入 `"Alice secret payload"`
  - Bob 写入 `"Bob public notes"`
- 各自读取 `GET /texts/confidential`：内容互不串扰，各得其值。
- Alice 执行 `DELETE /texts/confidential`：
  - Alice 自身查询返回 `404 Not Found`，`GET /texts` 返回空列表。
  - Bob 再次查询 `GET /texts/confidential`：内容完好无损（`"Bob public notes"`），不受任何影响。
  - **结论**：底层数据结构必须以 `(username, text_name)` 或分级字典 `Map<Username, Map<TextName, Content>>` 实现严格租户划分。

### 3. Invariant 3: 账号注销级联清理实测
- 注册用户 `charlie`，写入两条文本 `t1`, `t2`。
- 使用有效 Token 发起 `DELETE /users/me`：返回 `200 OK`。
- 紧接着使用原 Token 再次请求 `GET /texts`：立即返回 `401 Unauthorized`。
- 重新使用相同用户名 `charlie` 注册并登录（新密码）：
  - 查询 `GET /texts`：返回 `{"data": []}`，列表为空。
  - 查询 `GET /texts/t1`：返回 `404 Not Found`。
  - **结论**：注销必须原子化地级联清理用户信息、所有会话令牌与全部关联文本。

### 4. Invariant 4: 注销 × 登录并发竞争隔离实测
- 模拟攻击/异常竞争时序：
  - 线程 1 发起旧密码登录 `POST /sessions`（触发 100,000 次 PBKDF2 哈希运算耗时）。
  - 线程 2 并发执行 `DELETE /users/me` 注销旧账号，紧接着重新注册同名新账号并存入新数据 `"NEW_OWNER_DATA"`。
- 实测 5 轮高并发交错：
  - 轮次中，要么线程 1 登录在注销完成后到达，判定凭据失效返回 `401`；
  - 要么线程 1 提前签发了 Token，但该 Token 立即被随后的 `DELETE /users/me` 作废（返回 `401`）。
  - 没有任何一轮中，旧 Token 能越权读取到新账号名下的 `"NEW_OWNER_DATA"`。
