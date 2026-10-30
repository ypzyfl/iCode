# 需求：auth 登录状态埋点（aixcoding.auth logging）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

diagnostics 基建（`aixcoding.*` logger 子树 + F6 "aixcoding" tab + `aixcoding.log` 落盘）已随 diagnostics 批次合入，但尚无真实消费者，「埋点 → 面板呈现 + 落盘」闭环未经验证。登录异常（静默校验失败、token 被服务端拒绝、delegation 回退）目前无可查记录，用户报"登录不上"时排查只能靠复现。

## 目标与非目标

- 目标：
  - `LoginSession` 状态转换埋点：记录落 `aixcoding.auth` logger（diagnostics 基建的**首个真实消费者**）；
  - 闭环验证：launcher 启动 TUI → F6 "aixcoding" tab 呈现 + `~/.chrys/aixcoding-logs/aixcoding.log` 落盘。
- 非目标：
  - 不埋 `client.py`（device-code poll 每秒一次，记录即刷屏）；
  - 不改 diagnostics 基建（本批次纯消费，零基建改动）；
  - 不做遥测上报（telemetry 批次，殿后）；
  - 零上游文件改动（`session.py` 为定制层文件，ADR-0011 tier 布局）。

## 用户场景

1. 用户报登录异常 → 查 `aixcoding.log` 的 `aixcoding.auth` 记录，按消息定位命中分支（delegated/stored、成功/被拒/网络失败）；
2. TUI 中按 F6 → "aixcoding" tab 实时看启动静默校验结果（`tui.panel=true` 时，启动即有内容——`silent_login_check` 启动即调 `check_silent`）；
3. 桌面端子进程（delegation）父 token 被拒 → ERROR 记录"停止 shadow、回退 store"的降级行为。

## 验收标准

- [x] `session.py` 状态转换记录（design 定稿 12 条）全部落 `aixcoding.auth`，分级 INFO（成功与常规态，含用户取消）/ ERROR（静默校验失败全部分支 + 登录尝试失败——用户感知维度 AI 不可用即严重问题，design §分级原则）；
- [x] token / refresh_token / device_code / 异常 message 绝不出现在任何记录（测试反断言；记录字段白名单见 design）；
- [x] TUI 启动（`tui.panel=true`）→ F6 "aixcoding" tab 启动即见 silent check 记录（原表述"launcher 启动"——launcher 已退役 ADR-0013，由 `main()` 接线路径承载；2026-10-30 责任人目验通过）；
- [x] **全模式落盘**（2026-10-29 责任人裁决追加：仅 launcher 落盘不可接受）——直接 `icode`（TUI）、`icode run`（headless）、`icode acp` 等全部运行形态启动后 `aixcoding.log` 均有 sink（TUI 即有 silent check 记录；接线锚定 `app.py main()`，R2 报批见 design）（TUI 双通道实证 + `test_main_calls` 机器锚定全形态必经 `main()` 首行）；
- [x] `uv run pytest aixcoding/tests` 全绿（新增分支级 caplog 断言 + 接线测试）（2026-10-30：294 passed, 2 skipped）；
- [x] 上游文件改动仅 `app.py` 一处接线（R2 表，design §上游改动清单）（git status + 独立评审 R2 逐文件比对）。

## 开放问题

- 无（埋点清单与脱敏口径 design 定稿。注：交接要点记"8 处埋点"，逐分支核对 10 条 + 双 AI 评审 F4 补 `complete_login` 失败路径 2 条（责任人裁决选 A），定稿 12 条，偏差已在 design §埋点清单说明）。
