# HTTP 用户文本服务协议：官方参考服务端错误码矩阵实测表

> 测试时间: 2026-09-21 16:57:45
> 测试目标: 官方参考程序 `rm-server-async.exe` (`reference-v0.2.0`, x86_64-pc-windows-msvc)

| 状态码分类 | 测试用例名称 | 方法 | 路径 | 期望码 | 实际码 | 判定 | 官方响应摘要 |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **400** | 非法 JSON 语法 | `POST` | `/echo` | `400` | `400` | ✅ PASS | `{"message":"Expected UTF-8 JSON"}` |
| **400** | 请求体为 Array 而非 Object | `POST` | `/echo` | `400` | `400` | ✅ PASS | `{"message":"Expected only the string field text"}` |
| **400** | 请求体为原始 String 而非 Object | `POST` | `/echo` | `400` | `400` | ✅ PASS | `{"message":"Expected only the string field text"}` |
| **400** | 注册缺少 password 字段 | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Expected username and password strings"}` |
| **400** | 登录缺少 username 字段 | `POST` | `/sessions` | `400` | `400` | ✅ PASS | `{"message":"Expected username and password strings"}` |
| **400** | 回显缺少 text 字段 | `POST` | `/echo` | `400` | `400` | ✅ PASS | `{"message":"Expected only the string field text"}` |
| **400** | 回显包含未知多余字段 | `POST` | `/echo` | `400` | `400` | ✅ PASS | `{"message":"Expected only the string field text"}` |
| **400** | 注册包含未知多余字段 | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | text 为整数而非字符串 | `POST` | `/echo` | `400` | `400` | ✅ PASS | `{"message":"Expected only the string field text"}` |
| **400** | username 为整数而非字符串 | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Expected username and password strings"}` |
| **400** | 用户名为空字符串 (长度 0) | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | 用户名超长 (33 字符) | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | 用户名包含非法字符 (@) | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | 用户名包含非 ASCII 字符 (汉字) | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | 密码过短 (ASCII 5 字符 < 8) | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | 密码过短 (7 个 Emoji 标量值 < 8，虽 UTF-8 占 28 字节) | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | 密码过长 (129 字符 > 128) | `POST` | `/users` | `400` | `400` | ✅ PASS | `{"message":"Invalid account fields"}` |
| **400** | 文本名称超长 (65 字符 > 64) | `PUT` | `/texts/{name}` | `400` | `400` | ✅ PASS | `{"message":"Invalid text name"}` |
| **400** | 文本名称包含非法字符 (*) | `PUT` | `/texts/{name}` | `400` | `400` | ✅ PASS | `{"message":"Invalid text name"}` |
| **400** | 文本名称包含非 ASCII 字符 | `PUT` | `/texts/{name}` | `400` | `400` | ✅ PASS | `{"message":"Invalid text name"}` |
| **401** | 登录：用户名不存在 | `POST` | `/sessions` | `401` | `401` | ✅ PASS | `{"message":"Invalid username or password"}` |
| **401** | 登录：密码错误 | `POST` | `/sessions` | `401` | `401` | ✅ PASS | `{"message":"Invalid username or password"}` |
| **401** | 受保护接口：完全无 Authorization 请求头 | `GET` | `/texts` | `401` | `401` | ✅ PASS | `{"message":"Please log in again"}` |
| **401** | 受保护接口：缺少 Bearer 前缀 | `GET` | `/texts` | `401` | `401` | ✅ PASS | `{"message":"Please log in again"}` |
| **401** | 受保护接口：伪造无效 Token | `GET` | `/texts` | `401` | `401` | ✅ PASS | `{"message":"Please log in again"}` |
| **401** | 受保护接口：使用已登出(撤销)的 Token | `GET` | `/texts` | `401` | `401` | ✅ PASS | `{"message":"Please log in again"}` |
| **401** | 使用已撤销 Token 重复登出 | `DELETE` | `/sessions/current` | `401` | `401` | ✅ PASS | `{"message":"Please log in again"}` |
| **401** | 受保护接口：使用已注销用户的 Token | `GET` | `/texts` | `401` | `401` | ✅ PASS | `{"message":"Please log in again"}` |
| **404** | 访问完全不存在的 URL 路径 | `GET` | `/unknown/path/never/exists` | `404` | `404` | ✅ PASS | `{"message":"Unknown path"}` |
| **404** | 获取当前用户不存在的笔记 | `GET` | `/texts/{name}` | `404` | `404` | ✅ PASS | `{"message":"Text not found"}` |
| **404** | 删除当前用户不存在的笔记 | `DELETE` | `/texts/{name}` | `404` | `404` | ✅ PASS | `{"message":"Text not found"}` |
| **405** | GET /ping 误用 POST 请求 | `POST` | `/ping` | `405` | `405` | ✅ PASS | `{"message":"Method not allowed"}` |
| **405** | POST /users 误用 GET 请求 | `GET` | `/users` | `405` | `405` | ✅ PASS | `{"message":"Method not allowed"}` |
| **405** | POST /sessions 误用 GET 请求 | `GET` | `/sessions` | `405` | `405` | ✅ PASS | `{"message":"Method not allowed"}` |
| **405** | GET /texts 误用 POST 请求 | `POST` | `/texts` | `405` | `405` | ✅ PASS | `{"message":"Method not allowed"}` |
| **409** | 重复注册已存在的用户名 | `POST` | `/users` | `409` | `409` | ✅ PASS | `{"message":"Username exists"}` |
| **413** | 回显文本 UTF-8 超过 65,536 字节 (65,537 字节) | `POST` | `/echo` | `413` | `413` | ✅ PASS | `{"message":"Text exceeds 65536 UTF-8 bytes"}` |
| **413** | 上传笔记文本 UTF-8 超过 65,536 字节 (65,537 字节) | `PUT` | `/texts/{name}` | `413` | `413` | ✅ PASS | `{"message":"Text exceeds 65536 UTF-8 bytes"}` |
| **413_EDGE** | 回显文本刚好等于上限 65,536 字节 (预期 200 成功) | `POST` | `/echo` | `200` | `200` | ✅ PASS | `{"data":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...` |
| **413** | HTTP 请求体整体超过 524,288 字节 (524,289 字节) | `POST` | `/echo` | `413` | `413` | ✅ PASS | `{"message":"Request body too large"}` |

**统计**: 共执行 **40** 项边界与错误测试，通过 **40** 项，失败 **0** 项。
