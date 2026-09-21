import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

BASE_URL = "http://127.0.0.1:7878"

# 结果收集器
results: List[Dict[str, Any]] = []


def record(
    category: str,
    name: str,
    method: str,
    path: str,
    expected_status: int,
    actual_status: int,
    response_body: str,
    details: str = "",
):
    passed = actual_status == expected_status
    status_str = "PASS" if passed else "FAIL"
    print(
        f"[{status_str}] {category} - {name}: expected {expected_status}, got {actual_status}"
    )
    if not passed:
        print(f"       -> Response: {response_body[:200]}")
    results.append(
        {
            "category": category,
            "name": name,
            "method": method,
            "path": path,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "passed": passed,
            "response_body": response_body,
            "details": details,
        }
    )


def setup_benchmark_user(client: httpx.Client):
    """准备一个基准合法用户和有效 Token，供后续受保护接口测试使用"""
    uname = f"bench_{int(time.time())}"
    pwd = "password123"
    # 注册
    r = client.post("/users", json={"username": uname, "password": pwd})
    assert r.status_code == 201, f"Setup user failed: {r.text}"
    # 登录
    r = client.post("/sessions", json={"username": uname, "password": pwd})
    assert r.status_code == 200, f"Setup login failed: {r.text}"
    token = r.json()["data"]["token"]
    return uname, pwd, token


def run_tests():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    print("=== 准备基准测试用户 ===")
    uname, pwd, token = setup_benchmark_user(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    print(f"基准用户已就绪: {uname}, Token: {token[:12]}...\n")

    print("=== 1. 400 Bad Request 矩阵测试 ===")
    # 1.1 非法 JSON 语法
    r = client.post(
        "/echo",
        content=b"{malformed_json: true",
        headers={"Content-Type": "application/json"},
    )
    record("400", "非法 JSON 语法", "POST", "/echo", 400, r.status_code, r.text)

    # 1.2 请求体不是对象 (Array / String / Number)
    r = client.post("/echo", json=["text", "hello"])
    record("400", "请求体为 Array 而非 Object", "POST", "/echo", 400, r.status_code, r.text)

    r = client.post("/echo", json="just a string")
    record("400", "请求体为原始 String 而非 Object", "POST", "/echo", 400, r.status_code, r.text)

    # 1.3 缺少必填字段
    r = client.post("/users", json={"username": f"user_missing_{int(time.time())}"})
    record("400", "注册缺少 password 字段", "POST", "/users", 400, r.status_code, r.text)

    r = client.post("/sessions", json={"password": "password123"})
    record("400", "登录缺少 username 字段", "POST", "/sessions", 400, r.status_code, r.text)

    r = client.post("/echo", json={})
    record("400", "回显缺少 text 字段", "POST", "/echo", 400, r.status_code, r.text)

    # 1.4 多余字段 (协议明确规定只允许列出的字段)
    r = client.post(
        "/echo",
        json={"text": "hello", "extra_field": "not allowed"},
    )
    record("400", "回显包含未知多余字段", "POST", "/echo", 400, r.status_code, r.text)

    r = client.post(
        "/users",
        json={"username": f"u_extra_{int(time.time())}", "password": "password123", "tag": "admin"},
    )
    record("400", "注册包含未知多余字段", "POST", "/users", 400, r.status_code, r.text)

    # 1.5 字段类型不匹配 (类型不自动转换)
    r = client.post("/echo", json={"text": 12345})
    record("400", "text 为整数而非字符串", "POST", "/echo", 400, r.status_code, r.text)

    r = client.post("/users", json={"username": 12345, "password": "password123"})
    record("400", "username 为整数而非字符串", "POST", "/users", 400, r.status_code, r.text)

    # 1.6 用户名合法性规则 (1~32 ASCII 字母、数字、下划线、连字符)
    r = client.post("/users", json={"username": "", "password": "password123"})
    record("400", "用户名为空字符串 (长度 0)", "POST", "/users", 400, r.status_code, r.text)

    r = client.post("/users", json={"username": "a" * 33, "password": "password123"})
    record("400", "用户名超长 (33 字符)", "POST", "/users", 400, r.status_code, r.text)

    r = client.post("/users", json={"username": "user@name", "password": "password123"})
    record("400", "用户名包含非法字符 (@)", "POST", "/users", 400, r.status_code, r.text)

    r = client.post("/users", json={"username": "用户甲", "password": "password123"})
    record("400", "用户名包含非 ASCII 字符 (汉字)", "POST", "/users", 400, r.status_code, r.text)

    # 1.7 密码合法性规则 (8~128 Unicode 标量值)
    r = client.post("/users", json={"username": f"u_pwd_{int(time.time())}_1", "password": "short"})
    record("400", "密码过短 (ASCII 5 字符 < 8)", "POST", "/users", 400, r.status_code, r.text)

    r = client.post(
        "/users",
        json={"username": f"u_pwd_{int(time.time())}_2", "password": "😀" * 7},
    )
    record("400", "密码过短 (7 个 Emoji 标量值 < 8，虽 UTF-8 占 28 字节)", "POST", "/users", 400, r.status_code, r.text)

    r = client.post("/users", json={"username": f"u_pwd_{int(time.time())}_3", "password": "a" * 129})
    record("400", "密码过长 (129 字符 > 128)", "POST", "/users", 400, r.status_code, r.text)

    # 1.8 文本名称合法性规则 (1~64 ASCII 字母、数字、下划线、连字符)
    r = client.put(f"/texts/{'a' * 65}", json={"text": "hello"}, headers=auth_headers)
    record("400", "文本名称超长 (65 字符 > 64)", "PUT", "/texts/{name}", 400, r.status_code, r.text)

    r = client.put("/texts/bad*name", json={"text": "hello"}, headers=auth_headers)
    record("400", "文本名称包含非法字符 (*)", "PUT", "/texts/{name}", 400, r.status_code, r.text)

    r = client.put("/texts/中文笔记", json={"text": "hello"}, headers=auth_headers)
    record("400", "文本名称包含非 ASCII 字符", "PUT", "/texts/{name}", 400, r.status_code, r.text)

    print("\n=== 2. 401 Unauthorized 矩阵测试 ===")
    # 2.1 登录时用户名不存在
    r = client.post(
        "/sessions",
        json={"username": f"nonexistent_{int(time.time())}", "password": "password123"},
    )
    record("401", "登录：用户名不存在", "POST", "/sessions", 401, r.status_code, r.text)

    # 2.2 登录时密码错误
    r = client.post("/sessions", json={"username": uname, "password": "wrongpassword"})
    record("401", "登录：密码错误", "POST", "/sessions", 401, r.status_code, r.text)

    # 2.3 受保护接口：缺失 Authorization 请求头
    r = client.get("/texts")
    record("401", "受保护接口：完全无 Authorization 请求头", "GET", "/texts", 401, r.status_code, r.text)

    # 2.4 受保护接口：Authorization 头格式错误 (缺 Bearer 前缀)
    r = client.get("/texts", headers={"Authorization": token})
    record("401", "受保护接口：缺少 Bearer 前缀", "GET", "/texts", 401, r.status_code, r.text)

    # 2.5 受保护接口：无效 Token
    r = client.get("/texts", headers={"Authorization": "Bearer totally_fake_token_value_xyz"})
    record("401", "受保护接口：伪造无效 Token", "GET", "/texts", 401, r.status_code, r.text)

    # 2.6 受保护接口：登出后的 Token (已撤销)
    # 创建专门测试登出的临时用户
    temp_u = f"tmp_logout_{int(time.time())}"
    client.post("/users", json={"username": temp_u, "password": "password123"})
    r = client.post("/sessions", json={"username": temp_u, "password": "password123"})
    temp_token = r.json()["data"]["token"]
    temp_headers = {"Authorization": f"Bearer {temp_token}"}
    # 登出
    r = client.delete("/sessions/current", headers=temp_headers)
    assert r.status_code == 200
    # 再次使用该 token 请求受保护接口
    r = client.get("/texts", headers=temp_headers)
    record("401", "受保护接口：使用已登出(撤销)的 Token", "GET", "/texts", 401, r.status_code, r.text)

    # 重复登出
    r = client.delete("/sessions/current", headers=temp_headers)
    record("401", "使用已撤销 Token 重复登出", "DELETE", "/sessions/current", 401, r.status_code, r.text)

    # 2.7 受保护接口：注销账号后的 Token (级联失效)
    temp_del_u = f"tmp_del_{int(time.time())}"
    client.post("/users", json={"username": temp_del_u, "password": "password123"})
    r = client.post("/sessions", json={"username": temp_del_u, "password": "password123"})
    del_token = r.json()["data"]["token"]
    del_headers = {"Authorization": f"Bearer {del_token}"}
    # 注销账号
    r = client.delete("/users/me", headers=del_headers)
    assert r.status_code == 200
    # 再次使用已注销账号的 token
    r = client.get("/texts", headers=del_headers)
    record("401", "受保护接口：使用已注销用户的 Token", "GET", "/texts", 401, r.status_code, r.text)

    print("\n=== 3. 404 Not Found 矩阵测试 ===")
    # 3.1 未知路由
    r = client.get("/unknown/path/never/exists")
    record("404", "访问完全不存在的 URL 路径", "GET", "/unknown/path/never/exists", 404, r.status_code, r.text)

    # 3.2 获取不存在的笔记
    r = client.get("/texts/note_never_created_before", headers=auth_headers)
    record("404", "获取当前用户不存在的笔记", "GET", "/texts/{name}", 404, r.status_code, r.text)

    # 3.3 删除不存在的笔记
    r = client.delete("/texts/note_never_created_before", headers=auth_headers)
    record("404", "删除当前用户不存在的笔记", "DELETE", "/texts/{name}", 404, r.status_code, r.text)

    print("\n=== 4. 405 Method Not Allowed 矩阵测试 ===")
    # 4.1 GET 接口使用 POST
    r = client.post("/ping")
    record("405", "GET /ping 误用 POST 请求", "POST", "/ping", 405, r.status_code, r.text)

    # 4.2 POST 接口使用 GET
    r = client.get("/users")
    record("405", "POST /users 误用 GET 请求", "GET", "/users", 405, r.status_code, r.text)

    r = client.get("/sessions")
    record("405", "POST /sessions 误用 GET 请求", "GET", "/sessions", 405, r.status_code, r.text)

    # 4.3 GET /texts 误用 POST
    r = client.post("/texts", headers=auth_headers, json={"text": "hello"})
    record("405", "GET /texts 误用 POST 请求", "POST", "/texts", 405, r.status_code, r.text)

    print("\n=== 5. 409 Conflict 矩阵测试 ===")
    # 5.1 重复注册已有用户名
    r = client.post("/users", json={"username": uname, "password": "new_password_123"})
    record("409", "重复注册已存在的用户名", "POST", "/users", 409, r.status_code, r.text)

    print("\n=== 6. 413 Payload Too Large 矩阵测试 ===")
    # 6.1 文本 UTF-8 超限 (上限 65,536 字节 -> 测试 65,537 字节)
    over_text = "a" * 65537
    r = client.post("/echo", json={"text": over_text})
    record("413", "回显文本 UTF-8 超过 65,536 字节 (65,537 字节)", "POST", "/echo", 413, r.status_code, r.text)

    r = client.put("/texts/large_note", json={"text": over_text}, headers=auth_headers)
    record("413", "上传笔记文本 UTF-8 超过 65,536 字节 (65,537 字节)", "PUT", "/texts/{name}", 413, r.status_code, r.text)

    # 6.2 文本刚好在边界 (65,536 字节 -> 应该成功 200)
    boundary_text = "a" * 65536
    r = client.post("/echo", json={"text": boundary_text})
    record("413_EDGE", "回显文本刚好等于上限 65,536 字节 (预期 200 成功)", "POST", "/echo", 200, r.status_code, r.text)

    # 6.3 请求体超过 524,288 字节 (测试整包超限)
    # 构造合法的 JSON，但总字节数达到 524,289 字节
    huge_padding = " " * (524289 - len('{"text":""}'))
    huge_body = f'{{"text":"{huge_padding}"}}'.encode("utf-8")
    r = client.post(
        "/echo",
        content=huge_body,
        headers={"Content-Type": "application/json"},
    )
    record("413", "HTTP 请求体整体超过 524,288 字节 (524,289 字节)", "POST", "/echo", 413, r.status_code, r.text)


def export_markdown_matrix(output_path: Path):
    """把测试记录输出为漂亮的 Markdown 矩阵表"""
    lines = [
        "# HTTP 用户文本服务协议：官方参考服务端错误码矩阵实测表",
        "",
        f"> 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "> 测试目标: 官方参考程序 `rm-server-async.exe` (`reference-v0.2.0`, x86_64-pc-windows-msvc)",
        "",
        "| 状态码分类 | 测试用例名称 | 方法 | 路径 | 期望码 | 实际码 | 判定 | 官方响应摘要 |",
        "| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :--- |",
    ]
    for item in results:
        passed_icon = "✅ PASS" if item["passed"] else "❌ FAIL"
        # 简化响应文本以放入表格
        resp_snippet = item["response_body"].replace("\n", " ").replace("|", "\\|")
        if len(resp_snippet) > 60:
            resp_snippet = resp_snippet[:57] + "..."
        lines.append(
            f"| **{item['category']}** | {item['name']} | `{item['method']}` | `{item['path']}` | `{item['expected_status']}` | `{item['actual_status']}` | {passed_icon} | `{resp_snippet}` |"
        )

    lines.append("")
    total = len(results)
    passed_cnt = sum(1 for r in results if r["passed"])
    lines.append(f"**统计**: 共执行 **{total}** 项边界与错误测试，通过 **{passed_cnt}** 项，失败 **{total - passed_cnt}** 项。")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[Matrix Exported] 矩阵报告已生成: {output_path.resolve()}")


if __name__ == "__main__":
    run_tests()
    out_file = Path(__file__).parent / "error-matrix.md"
    export_markdown_matrix(out_file)
