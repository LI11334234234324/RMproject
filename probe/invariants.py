import concurrent.futures
import subprocess
import sys
import time
from pathlib import Path
import httpx

SERVER_EXE = (
    Path(__file__).resolve().parent.parent
    / "rm-projects-rust-windows-x86_64-reference-v0.2.0"
    / "rm-server-async.exe"
)


def run_server_context(address: str, ttl_seconds: int = 300):
    """Context manager / helper to run rm-server-async in background and cleanly terminate it."""
    class ServerContext:
        def __init__(self):
            self.process = None

        def __enter__(self):
            cmd = [
                str(SERVER_EXE),
                "--address",
                address,
                "--token-ttl-seconds",
                str(ttl_seconds),
            ]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Wait for server to become responsive
            base_url = f"http://{address}"
            client = httpx.Client(base_url=base_url, timeout=2.0)
            start_time = time.time()
            connected = False
            while time.time() - start_time < 5.0:
                try:
                    r = client.get("/ping")
                    if r.status_code == 200:
                        connected = True
                        break
                except Exception:
                    pass
                time.sleep(0.05)
            client.close()
            if not connected:
                self.process.terminate()
                raise RuntimeError(f"Server failed to start on {address}")
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()

    return ServerContext()


def test_invariant_1_ttl():
    print("\n--- [Invariant 1] 固定 TTL 不续期 (Token TTL & Non-sliding Expiry) ---")
    addr = "127.0.0.1:7891"
    base_url = f"http://{addr}"
    # Start server with TTL = 2s
    with run_server_context(addr, ttl_seconds=2):
        client = httpx.Client(base_url=base_url, timeout=3.0)
        # 1. 注册并登录
        client.post("/users", json={"username": "alice", "password": "password123"})
        r_login = client.post("/sessions", json={"username": "alice", "password": "password123"})
        assert r_login.status_code == 200
        token = r_login.json()["data"]["token"]
        expires_in = r_login.json()["data"]["expires_in"]
        assert expires_in == 2
        auth = {"Authorization": f"Bearer {token}"}
        print(f"  [+] 成功登录，获取到 Token (TTL={expires_in}s)")

        # 2. 在 0.5s 时发请求
        time.sleep(0.5)
        r = client.get("/texts", headers=auth)
        assert r.status_code == 200, f"Expected 200 at 0.5s, got {r.status_code}"
        print("  [+] t=0.5s: GET /texts 正常响应 200")

        # 3. 在 1.2s 时发请求（产生写操作）
        time.sleep(0.7)
        r = client.put("/texts/k1", json={"text": "v1"}, headers=auth)
        assert r.status_code == 200, f"Expected 200 at 1.2s, got {r.status_code}"
        print("  [+] t=1.2s: PUT /texts/k1 正常响应 200")

        # 4. 在 2.3s 时发请求 (距离登录已经过去 > 2.0s，但距离上一次请求仅 1.1s)
        # 如果是滑动过期（sliding expiration），此时应该成功；但本协议要求固定 TTL 不续期，必须报 401！
        time.sleep(1.1)
        r = client.get("/texts", headers=auth)
        print(f"  [+] t=2.3s: GET /texts 返回状态码: {r.status_code}, 响应: {r.json()}")
        assert r.status_code == 401, f"Expected 401 after TTL expiry, got {r.status_code}"
        assert r.json() == {"message": "Please log in again"}
        print("  [PASS] 成功证实：中间所有业务请求均不延长 Token 有效期，到期立即失效！")


def test_invariant_2_tenant_isolation():
    print("\n--- [Invariant 2] 租户完全隔离 (Tenant Isolation) ---")
    addr = "127.0.0.1:7892"
    base_url = f"http://{addr}"
    with run_server_context(addr, ttl_seconds=60):
        client = httpx.Client(base_url=base_url, timeout=3.0)
        # 1. 注册两个用户
        client.post("/users", json={"username": "alice", "password": "password123"})
        client.post("/users", json={"username": "bob", "password": "password123"})
        token_a = client.post("/sessions", json={"username": "alice", "password": "password123"}).json()["data"]["token"]
        token_b = client.post("/sessions", json={"username": "bob", "password": "password123"}).json()["data"]["token"]
        auth_a = {"Authorization": f"Bearer {token_a}"}
        auth_b = {"Authorization": f"Bearer {token_b}"}

        # 2. 两人各自创建同名文本 'confidential'，内容不同
        client.put("/texts/confidential", json={"text": "Alice secret payload"}, headers=auth_a)
        client.put("/texts/confidential", json={"text": "Bob public notes"}, headers=auth_b)

        # 3. 验证各自读取到的内容完全独立
        res_a = client.get("/texts/confidential", headers=auth_a).json()["data"]
        res_b = client.get("/texts/confidential", headers=auth_b).json()["data"]
        assert res_a == "Alice secret payload"
        assert res_b == "Bob public notes"
        print("  [+] Alice 与 Bob 同名文件 'confidential' 读取内容严格独立")

        # 4. Alice 删除该文本
        del_a = client.delete("/texts/confidential", headers=auth_a)
        assert del_a.status_code == 200
        # Alice 查自己应是 404
        assert client.get("/texts/confidential", headers=auth_a).status_code == 404
        assert client.get("/texts", headers=auth_a).json()["data"] == []

        # Bob 查自己依然存在且不受任何影响
        assert client.get("/texts/confidential", headers=auth_b).status_code == 200
        assert client.get("/texts/confidential", headers=auth_b).json()["data"] == "Bob public notes"
        assert client.get("/texts", headers=auth_b).json()["data"] == ["confidential"]
        print("  [PASS] 成功证实：不同租户命名空间完全独立，互不可见、不可修改、删除互不干扰！")


def test_invariant_3_cascade_deregistration():
    print("\n--- [Invariant 3] 级联注销清理 (Cascade Deletion on Deregistration) ---")
    addr = "127.0.0.1:7893"
    base_url = f"http://{addr}"
    with run_server_context(addr, ttl_seconds=60):
        client = httpx.Client(base_url=base_url, timeout=3.0)
        # 1. 注册 charlie，写入数据
        client.post("/users", json={"username": "charlie", "password": "password123"})
        token_c = client.post("/sessions", json={"username": "charlie", "password": "password123"}).json()["data"]["token"]
        auth_c = {"Authorization": f"Bearer {token_c}"}
        client.put("/texts/t1", json={"text": "note 1"}, headers=auth_c)
        client.put("/texts/t2", json={"text": "note 2"}, headers=auth_c)
        assert len(client.get("/texts", headers=auth_c).json()["data"]) == 2

        # 2. Charlie 注销账号 DELETE /users/me
        r_del = client.delete("/users/me", headers=auth_c)
        assert r_del.status_code == 200
        print("  [+] 账号 charlie 成功注销 (DELETE /users/me -> 200)")

        # 3. 验证原 Token 立即失效 (返回 401)
        r_old_token = client.get("/texts", headers=auth_c)
        assert r_old_token.status_code == 401
        assert r_old_token.json() == {"message": "Please log in again"}
        print("  [+] 原 Token 立即失效 (401 Please log in again)")

        # 4. 同名重新注册 charlie
        r_reg_again = client.post("/users", json={"username": "charlie", "password": "new_password456"})
        assert r_reg_again.status_code == 201
        token_c_new = client.post("/sessions", json={"username": "charlie", "password": "new_password456"}).json()["data"]["token"]
        auth_c_new = {"Authorization": f"Bearer {token_c_new}"}
        print("  [+] 同名账号 charlie 重新注册成功")

        # 5. 验证名下所有数据已被全部级联清空，新账号列表为空
        list_res = client.get("/texts", headers=auth_c_new).json()["data"]
        assert list_res == [], f"Expected empty text list for recreated user, got {list_res}"
        assert client.get("/texts/t1", headers=auth_c_new).status_code == 404
        assert client.get("/texts/t2", headers=auth_c_new).status_code == 404
        print("  [PASS] 成功证实：注销账号将原子级联清理用户实体、Token 凭证与名下所有文本数据！")


def test_invariant_4_deregister_login_race():
    print("\n--- [Invariant 4] 注销与登录竞争隔离 (Deregistration-Login Race Immunity) ---")
    addr = "127.0.0.1:7894"
    base_url = f"http://{addr}"
    with run_server_context(addr, ttl_seconds=60):
        # 多轮并发竞争测试
        rounds = 5
        passed_rounds = 0

        for r in range(rounds):
            username = f"racer_{r}_{int(time.time()*1000)%10000}"
            old_pass = "old_password_1"
            new_pass = "new_password_2"

            client = httpx.Client(base_url=base_url, timeout=5.0)
            # 1. 注册初始账号并写入专有私密笔记
            client.post("/users", json={"username": username, "password": old_pass})
            t_init = client.post("/sessions", json={"username": username, "password": old_pass}).json()["data"]["token"]
            auth_init = {"Authorization": f"Bearer {t_init}"}
            client.put("/texts/secret", json={"text": "OLD_VICTIM_DATA"}, headers=auth_init)

            # 2. 并发操作：
            # 线程 A：用旧密码发起登录 POST /sessions（触发 100k 次哈希耗时）
            # 线程 B：同时注销该账号，并用新密码同名重新注册，存入新笔记 "NEW_OWNER_DATA"
            def do_login():
                c = httpx.Client(base_url=base_url, timeout=5.0)
                res = c.post("/sessions", json={"username": username, "password": old_pass})
                c.close()
                return res

            def do_deregister_and_recreate():
                c = httpx.Client(base_url=base_url, timeout=5.0)
                # 注销旧账号
                r_d = c.delete("/users/me", headers=auth_init)
                # 重新注册同名新账号
                r_r = c.post("/users", json={"username": username, "password": new_pass})
                # 新账号登录并写入新数据
                r_l = c.post("/sessions", json={"username": username, "password": new_pass})
                if r_l.status_code == 200:
                    t_new = r_l.json()["data"]["token"]
                    c.put("/texts/secret", json={"text": "NEW_OWNER_DATA"}, headers={"Authorization": f"Bearer {t_new}"})
                c.close()
                return r_d.status_code, r_r.status_code, r_l.status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                f_login = executor.submit(do_login)
                f_dereg = executor.submit(do_deregister_and_recreate)

                res_login = f_login.result()
                res_dereg = f_dereg.result()

            print(f"  Round {r}: login status = {res_login.status_code}, dereg/recreate = {res_dereg}")

            # 3. 核心安全不变式判定：
            # 只有当注销真正成功 (res_dereg[0] == 200) 时，旧账号才真正被清理过
            if res_dereg[0] == 200:
                # 注销成功了
                if res_login.status_code == 401:
                    # 登录在注销后被判定无效，符合预期
                    pass
                elif res_login.status_code == 200:
                    # 登录返回了 token，但既然旧账号已注销并重建，旧 token 绝对不能能读取新账号数据！
                    leaked_token = res_login.json()["data"]["token"]
                    probe_res = client.get("/texts/secret", headers={"Authorization": f"Bearer {leaked_token}"})
                    # 应该返回 401，且绝对不能读到新用户的数据
                    assert probe_res.status_code == 401 or probe_res.json().get("data") != "NEW_OWNER_DATA", (
                        f"RACE VIOLATION: Old token accessed new owner's data! "
                        f"Status: {probe_res.status_code}, Body: {probe_res.text}"
                    )
            else:
                print(f"    (注意: 注销未成功 r_d={res_dereg[0]}，此轮竞争旧 Token 提前使原会话失效)")

            client.close()
            passed_rounds += 1

        print(f"  [PASS] 成功通过 {passed_rounds}/{rounds} 轮注销-登录并发竞争测试，旧登录凭据绝对无法附着或访问新账号！")


def main():
    print("=========================================================")
    print("  RoboMaster 用户文本服务协议：官方参考服务端四大不变式实测")
    print(f"  测试二进制: {SERVER_EXE}")
    print("=========================================================")
    try:
        test_invariant_1_ttl()
        test_invariant_2_tenant_isolation()
        test_invariant_3_cascade_deregistration()
        test_invariant_4_deregister_login_race()
        print("\n[ALL INVARIANTS PASSED] 四大并发与生命周期不变式全部实测通过！")
    except Exception as e:
        print(f"\n[FAILED]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
