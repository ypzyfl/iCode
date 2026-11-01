# 验证证据：服务组合测试（composition-tests）

> 追加不删旧；每节 = 一次验证（命令 + 输出摘要 + 结论）。R7：未运行的验证不得描述为通过。

## V1（实施验证：单文件 + lint + 统一入口，2026-11-01，Windows 本机）

环境：Windows 11 本机，Python 3.14.8（.venv），大写盘符启动；配方 `set "PYTHONPATH="` +
`set "PYTHONUTF8=1"`。

| # | 命令 | 结果 |
|---|---|---|
| 1 | `uv run pytest aixcoding/tests/auth/test_composition_lifecycle.py -v -n0` | **1 passed in 3.09s**（首跑一次通过；含 auto 模式登录 ~1s poll 等待，与 F-07 时序基线吻合；format 后复跑 2.89s 仍绿） |
| 2 | `uv run ruff check aixcoding/` | All checks passed（初跑自动修复 2 处后干净） |
| 3 | `uv run ruff format --check aixcoding/` | 200 files already formatted（format 重排测试文件签名与 test-plan.md 代码块后干净） |
| 4 | `uv run python aixcoding/tools/verify.py --smart --paths aixcoding/tests/auth/test_composition_lifecycle.py` | **Summary: PASSED (exit 0)**——custom：`343 passed, 2 skipped in 10.79s`（8 workers，345 items = 基线 344 + 本批 1 用例；2 skip = catalog consumer 平台无关 auto-skip，与 P1-3 基线一致）；upstream：Smart Test 0 选择（纯 aixcoding/ 改动，上游 import 图内无消费者，预期） |

结论：

- 主链路组合用例一次通过：三次请求逐次快照断言（登录前无 `token` / 登录后
  `token == 登录签发值` / 登出后无 `token`；`Authorization == "Bearer k-test"` 三次不变）、
  快照计数基线 3、同一性断言（真实 `get_login_session()` 返回测试实例）、环境前置
  （三委托通道清理 + 包级真实 `detect_delegation() is None`）全部在案；
- 形态 A 七条件落码核对（AC1）：真实 `create_client` 工厂 ✓ / loopback（`bypass_proxy=True`
  隔离）✓ / 同一 client 实例三次请求 ✓ / 逐次结构化快照 ✓ / 真实 `LoginSession` +
  `CredentialStore` ✓ / `aixcoding/mock` auth 契约（auto 轮询）✓ / 登录态仅经
  `complete_login()` 建立（零手工注入、零直写 store）✓；
- 预算口径：定制套件 10.79s（并行）≪1min 分区评估阈值，无需分区；
- AC7 的 CI 半边以 **PR checks 本身**为证据（DEVELOPMENT.md §7：CI 结果不回写仓库，
  PR 创建后零追加留痕）——本文件不设"PR 后补记"章节；PR 描述引用 check 结论即可。
