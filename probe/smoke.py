import time

import httpx

BASE_URL = "http://127.0.0.1:7878"


def test_smoke():
    client = httpx.Client(base_url=BASE_URL)

    # 1. 连通性 ping
    r = client.get("/ping")
    print("1. Ping:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json() == {"data": "pong"}

    # 2. 回显 echo
    r = client.post("/echo", json={"text": "你好\nRM"})
    print("2. Echo:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json() == {"data": "你好\nRM"}

    # 3. 注册新用户 (用时间戳保证每次名字唯一)
    username = f"user_{int(time.time())}"
    password = "password123"
    r = client.post("/users", json={"username": username, "password": password})
    print("3. Register:", r.status_code, r.json())
    assert r.status_code == 201

    # 4. 登录拿到 Token
    r = client.post("/sessions", json={"username": username, "password": password})
    print("4. Login:", r.status_code, r.json())
    assert r.status_code == 200
    token = r.json()["data"]["token"]
    expires_in = r.json()["data"]["expires_in"]
    print(f"   -> 拿到 Token: {token[:10]}... 有效期: {expires_in}秒")

    # 后续受保护接口统一需要的请求头
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 5. 上传/存笔记 (PUT /texts/todo)
    note_name = "todo"
    note_content = "1. 搞定探针\n2. 学Rust\n3. 进RM战队"
    r = client.put(
        f"/texts/{note_name}", json={"text": note_content}, headers=auth_headers
    )
    print("5. Put text:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json() == {"data": None}

    # 6. 列出笔记 (GET /texts)
    r = client.get("/texts", headers=auth_headers)
    print("6. List texts:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json() == {"data": [note_name]}

    # 7. 读取单篇笔记 (GET /texts/todo)
    r = client.get(f"/texts/{note_name}", headers=auth_headers)
    print("7. Get text:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json() == {"data": note_content}

    # 8. 删除笔记 (DELETE /texts/todo)
    r = client.delete(f"/texts/{note_name}", headers=auth_headers)
    print("8. Delete text:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json() == {"data": None}

    # 9. 退出登录 (DELETE /sessions/current)
    r = client.delete("/sessions/current", headers=auth_headers)
    print("9. Logout:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json() == {"data": None}

    print("\n[PASS] 全部 9 个核心业务流程全量跑通！🎉")


if __name__ == "__main__":
    test_smoke()
