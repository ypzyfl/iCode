# 需求：护栏规则包调优——confirm 分档、网络黑名单与重新开启（guard-rule-tuning）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

`batches/guard-hooks` 迁入的 40 条规则按「confirm 一律先按 block 落地」执行，网络按
「白名单只放回环」执行。现场误报（命令链接 `&&`、Shell 内建 `source`/`eval`、提问里
出现注入 payload 字符串、任意非回环 IP）把日常开发打断到无法工作，于是 **PR #129
（`019abe38`）把两个受管 hook 出厂停用**——全停换可用性，保护归零，属于临时态。

用户提供《iCode 安全护栏测试用例：confirm 分档 + 网络黑名单》与对应改动包
（桌面 `iCode-guard-hooks-changes.zip`），要求：按误报复审结果调优规则包并合入，
**合入后安全护栏保持开启**。

## 目标与非目标

- 目标：
  1. 删除 7 条高风险误报规则（`IN-03`/`IN-04`/`IN-07`、`T-SHELL-03-1`/`T-SHELL-04`、
     `T-PY-02`/`T-NET-02`），并有回归用例钉住「保持删除」；
  2. 7 条中高风险规则改 confirm 出厂落地为 `ask`（确认框：继续→放行，拒绝→拦截；
     客户端无法询问时按 block 兜底）；
  3. 网络从白名单翻转为黑名单（出厂含 `*.bocsys.cn` 与 `22.122.49.168/32`；
     危险端口对非回环目标恒拦；回环（`127.0.0.0/8`、`::1`、`localhost`、`*.localhost`）
     完全豁免——危险端口也不例外，F2 裁决）；
  4. hooks.yaml 两个受管条目出厂重新开启（`enabled: true`）；
  5. 本机合入后护栏处于开启状态（安装 + `guardctl status` 确认）。
- 非目标：
  - 不改任何上游文件（零上游接触）；
  - 不动 `write_scope` 出厂值（ADR-0023 裁决维持）与 `guardctl` 开关语义；
  - 不实现流式输出层扫描（`rules.json` 的 scope 注记维持）；
  - 不新增第三方依赖、不新增豁免（R11/R13 无涉）。

## 用户场景

1. 日常开发不被打断：让模型执行 `ls -la && pwd`、`source .venv/bin/activate`，
   提问「`' or '1'='1` 能不能注入」「查一下 10.0.0.5」——全部放行。
2. 中高风险先确认：`rm -rf /tmp/testdir`、读 `~/.ssh/id_rsa` → TUI 弹
   「检测到较高风险操作，是否继续？」；继续→执行，拒绝→拦截（拒绝文案由引擎组合，
   非 `block_message`；headless 实测见 verification.md B16）；
   headless（`aixcoding-cli run`）无法询问，直接拦截。
3. 网络目标管控：`web_fetch` 访问 `*.bocsys.cn`、`22.122.49.168` → 拦截；未列入的
   `10.1.2.3`、`example.com` → 放行；`10.1.2.3:3389` 危险端口拦；`127.0.0.1:6379`、
   `localhost:6379` 放行（回环完全豁免，F2 裁决）。

## 验收标准

- [ ] `uv run python -m aixcoding.tests.guard.guard_pack_selftest` → `Ran 107 tests … OK (skipped=1)`
- [ ] `uv run pytest aixcoding/tests/guard -q` 全绿（测试用例文档基线 27 passed, 1 skipped；
      实际数字记入 verification.md）
- [ ] 临时目录部署验证（`AIXCODING_GUARD_HOOKS_DIR` 指向临时目录，不触碰本机配置）→
      `共 71 条，失败 0 条`
- [ ] `uv run ruff check` 与 `ruff format --check`（guard 相关路径）通过；
      `uv run ty check --error-on-warning`（win32 / linux / darwin）通过
- [ ] hooks.yaml 两个受管条目出厂 `enabled: true`；安装后 `guardctl status` 显示
      `规则：33 条 · 开 32 · 关 1`；`show IN-05` 为 confirm、`show T-NET-01` 为 block
- [ ] 已删 7 条规则有「保持删除」自检回归用例且通过
- [ ] confirm 规则在无法询问的环境按 block 兜底（引擎行为已核验，见 design 假设 1；
      手工用例 B16 覆盖 headless）
- [ ] 合入后本机护栏开启（安装到 `%APPDATA%\chrys\hooks\` 并确认状态）

## 开放问题

- 无：黑名单出厂条目（`*.bocsys.cn`、`22.122.49.168/32`）为业务给定禁止攻击目标，
  由 ADR 承载其长期维护义务；rules.json 两处过期 note 修正见 design 变更清单。
