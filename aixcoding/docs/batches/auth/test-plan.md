# 测试方案：auth 迁入

> 活文档：随时更新、不签认；质量由双 AI 自审与行为锚定测试本身保障。

## 测试范围与策略

三层，全部落 `aixcoding/tests/auth/`（B1/B3 边界内合法：import `chrys.*` 与 `aixcoding.mock.*`）：

1. **单元/契约层（随迁恢复，7 文件 93 例）**：旧分支 `tests/app/aixcoding/test_auth_*.py`
   原样迁移，import/env 字面量/mock 路径按 design 改写；mock 集成断言按 PR #56 fixture
   适配（`ehr=1234567`/`name=测试员`/`token_type=aixcoding-cli`，以实现为准）。
2. **行为锚定层（新增，`test_llm_token_wiring.py`）**：真调被改上游符号
   （`RequestHeaders.stamp` / `_login_token` / `_build_default_headers`）断言行为，
   **禁 mock 锚点本身**（DEVELOPMENT.md §5）：
   - 通道 1（extra_headers 侧，单元级）：`stamp()` 直接驱动——注入/不注入/早退三分支；
   - 通道 2（default_headers 合并语义，wire 级）：**真实 openai SDK client +
     `httpx.MockTransport` 观察 wire 头**（mock 只在 transport 层，SDK 的
     default_headers × per-request extra_headers 合并行为真实发生，不得 mock 掉）。
     **定性（评审 F-1 澄清）**：通道 2 是**外部依赖行为探针**——守护 design 对比二的
     hook 切换触发条件（SDK 合并语义漂移则红），不锚定本批实现（改坏 `stamp()` 注入行
     它不红）；本批实现半边由通道 1 两例强锚定。
3. **mock 端到端**（随迁恢复）：`TestLoopbackMockIntegration`（auto/manual 两模式全流程）。

登录态注入手段：`LoginSession` 全参可注入构造（`store=CredentialStore(tmp_path,
backend=MemoryBackend())` 预存 credential）+ `get_login_session()` 单例替换
（monkeypatch），不落真实 config dir、零网络（stored_token 无 IO）。

## 覆盖矩阵

| 验收标准 | 测试入口（文件::用例） | 类型 |
|---|---|---|
| 有登录态 → 请求带 `token` 头 | test_llm_token_wiring.py::test_stamp_injects_token | 行为锚定（通道 1） |
| 无登录态/会话异常 → 不带头、请求照发 | test_llm_token_wiring.py::test_no_session_no_header | 行为锚定 |
| `_login_token()` 全吞错返回 "" | test_llm_token_wiring.py::test_login_token_swallows | 行为锚定 |
| 登录 token 覆盖 caller `extra_headers` 静态 token | test_llm_token_wiring.py::test_overrides_extra_headers | 行为锚定（通道 1） |
| 登录 token 覆盖 `profile.http_headers` 静态 token（0.28 credential-authoritative） | test_llm_token_wiring.py::test_overrides_default_headers_on_wire | 行为锚定（通道 2，wire 级） |
| stamp() import 失败不炸请求（try 包裹） | test_llm_token_wiring.py::test_stamp_survives_import_failure | 行为锚定（注入坏模块路径） |
| 登出后下一请求失效 | test_llm_token_wiring.py::test_logout_takes_effect_next_request | 行为锚定 |
| env 更名后解析档位正确（含 fall back PROD） | test_auth_environments.py（随迁 6 例） | 单元 |
| 设备码全流程（auto/manual） | test_auth_client.py::TestLoopbackMockIntegration | 端到端 |
| 存储加密信封/腐蚀自清/委托检测 | test_auth_storage / _crypto / _delegation（随迁） | 单元 |

## 异常与降级路径

- 会话不可用（auth 包 import 失败/存储腐蚀/后端降级）→ `_login_token()` 全吞返回 ""，
  请求无 token 头照发（`test_no_session_no_header` + `test_login_token_swallows`）；
- stamp() 内 import 抛错 → try 兜底 `login_token=""`，不阻断请求（`test_stamp_survives_import_failure`）；
- credential 过期 → `stored_token` 返回 None，表现同未登录（design 假设 8 已知边界，
  `test_auth_types` 的 is_expired 单元例随迁覆盖）。

## 手工验证步骤（若需）

mock 联调冒烟（tui 批次前的登录链路演示）：`python -m aixcoding.mock`（默认组合）→
`AIXCODING_AUTH_ENVIRONMENT=local uv run icode run "hi"`（无登录态时 LLM 请求无 token 头，
不阻断）；结果记 verification.md。完整"对话框 mock 登录"冒烟留 tui 批次。
