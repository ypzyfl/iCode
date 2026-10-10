# LLM 模型对接说明：获取 token 与用户 ID

> 面向：需要用户 token 和用户 ID 来访问 LLM 模型的下游代码（跑在 icode 进程内）。
> 更新日期：2026-10-08。API 定义：`aixcoding/auth/session.py`。

---

## 1. 两行代码拿 token 和用户 ID

```python
from aixcoding.auth import get_login_session

s = get_login_session()
token = s.stored_token        # str | None —— 用户 token
user_id = s.stored_user_id    # str | None —— 用户 ID（ehr 工号）
```

**不用关心用户是怎么登录的。** 两种场景同一个 API，属性内部自动选来源：

| 场景 | 登录方式 | `stored_token` 来源 | `stored_user_id` 来源 |
|---|---|---|---|
| 独立 TUI | 用户在 icode 里 `/login`（设备码） | 本地加密存储的凭据 | 同一凭据的 `userId` 字段 |
| 桌面端集成 | AIxCoding 桌面端登录后拉起 icode | 桌面端透传的 token（内存） | 桌面端透传的 ehr |

`None` = 未登录 / 凭据过期 / 存储损坏 / 环境档位不匹配 / 桌面端 token 已被服务端拒绝。拿到 `None` 就引导用户登录（独立场景）或让桌面端重登（集成场景），不要重试。

## 2. 判定当前场景（可选）

```python
if s.delegated_credential is not None:
    # 桌面端托管会话：delegated_credential.ehr / .display_name / .source 可用
    ...
```

## 3. 需要完整身份（姓名、部门等）

```python
account = await s.check_silent()   # AccountInfo | None，走一次 user/info 网络校验
```

返回 `None` 表示当前凭据无效或网络不可达；网络故障**不会**清除凭据（离线不是登出），服务端拒绝才会。

## 4. 注意事项

1. **token 取一次，构建客户端时持有**。`stored_token` 每次调用都会重新读盘 + 解密（独立场景），不要放在每请求的路径上。
2. **`check_silent()` 有副作用**：服务端拒绝后会清理/取消凭据，之后 `stored_token` 变 `None`。取 token 和做校验之间不要假设登录态不变。
3. **只在 icode 进程内用**。这是进程内 API，不是跨进程的文件共享；同事的代码需要在 icode 的 Python 进程里 import（例如模型客户端装配处）。
4. **环境档位**：`CHRYS_AUTH_ENVIRONMENT`（local/dev/prod，默认 prod）决定读哪份凭据。始终通过 session 取，**不要绕过去直读 `users/<env>/private/secrets/` 下的文件**——Windows 是 DPAPI 加密，直接读拿不到明文，且存储格式不承诺稳定。
5. **不要打印或落盘 token**。日志、trajectory、异常消息里都不要出现它。
6. 桌面端主通道（`CHRYS_AUTH_DELEGATED_TOKEN`）若没带 `CHRYS_AUTH_DELEGATED_EHR`，`stored_user_id` 在桌面场景可能为 `None`；兼容通道（`AIXCODING_USER_EHR`）总是有值。需要兜底就用 `await s.check_silent()` 的 `account.ehr`。

## 5. 快速自检（icode 环境里跑，输出含明文 token——仅本机调试，勿外发/截图）

```bash
uv run python -c "from aixcoding.auth import get_login_session as g; s=g(); print('token:', s.stored_token, '| user_id:', s.stored_user_id)"
```

输出 `token: <token 明文> | user_id: 8769092` 即对接就绪（TUI 先 `/login`，或由桌面端拉起）；未登录时输出 `token: None | user_id: None`。给他人演示时用 `bool(s.stored_token)` 只看有无即可。
