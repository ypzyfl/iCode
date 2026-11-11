# 需求：追上游 v0.35.2（upstream-merge-v0.35.2）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

上游 iCode 已发布 v0.35.2（release tag v0.35.2 = `2fd777f626649d53d7ccd701e26a1a7ada569ce8`，
2026-11-10 发布）。本 fork 主线 `main_aixcoding_cli` 基线为 0.35.1
（UPGRADE-RUNBOOK.md 头部「当前基线」节，2026-11-09 完成追平；当前分支头 `d52626f1`，
该头已包含 catalog-auto-sync / parallel-batch-governance / user-manual 等批次）。
DEVELOPMENT.md §8 升级节奏条款：每次上游发布后评估跟进，长期不升级是需显式决策的风险状态。

责任人 2026-11-11 开工裁决：

1. 按完整升级管线开工（微改动豁免不适用）；
2. merge 目标 ref = **release tag v0.35.2（commit `2fd777f`）**，非镜像头；
3. 镜像同步已由责任人手动完成：本地/`origin/main_iCode` 均在 `3ea2ca2a`，
   且 `2fd777f` 是其祖先（镜像头领先 31 提交 / 25 非合并；镜像领先不影响 merge 目标）；
4. **手册内容与追上游解耦**（2026-11-11 裁决）：`aixcoding/manual/` 是完整定制手册，
   升级批次不做上游 `docs/` → manual 的内容对账；手册跟进上游由独立手册批次处理。

区间 `v0.35.1(7c423b06)..v0.35.2(2fd777f)` 共 38 提交（29 非合并）、149 文件、
+8650/−1381；`merge-tree` 干跑实测文本冲突 **1 处**（见 design）。

## 目标与非目标

- 目标：`main_aixcoding_cli` 基线追至 **v0.35.2**，全部在册定制点存活且验证全绿。
- 非目标：
  - 不借升级顺手做定制功能开发；
  - 不同步 `aixcoding/manual/` 内容、不重放手册定制、不因手册内容重出 wheel/PDF
    （上游 `docs/` 自身变更随 merge 带入；手册跟进另立批次）；
  - 旧分支 `main_aixcoding_cli_0.28.0_final` 按冻结条款不随升级（runbook §8）。

## 上游区间重点变更（v0.35.1..v0.35.2）

1. **会话浏览器大改**：搜索从"当前页"扩展到全部所选会话（ID/标题/目录/提示词），
   结果分页；每个会话的 meta 进入浏览器快照（`sessions/presenter.py`、
   `sessions/screen.py`、`session_listing.py`、`store.py`）。
2. **提示词编辑器整稿编辑**：编辑器展开 labels/fields 后编辑全文；粘贴标签可单独编辑，
   保存为一次 undo；`main/screen.py` +116 行、`draft_text_area.py`、`prompt_draft.py`、
   `vim.py` 等编辑链路重构。
3. **skills 资源两层发现**：Skill 根层及下两级子目录内的资源可被发现
   （`skills/loader.py`）。
4. **MCP 稳定性**：每个掉线 session 重连一次、refresh 时替换 catalog
   （`mcp/_connection.py`、`adapter.py`、`owned.py`）。
5. **kernel 修复与性能**：流式 text/reasoning 一遍合并、浮点整数/Enum 序列化与
   tool schema 修复、非法 tool 参数报错而非失败整个 turn。
6. **TUI 修复**：trajectory 轴标签先换单位再舍入、shutdown 清空 screen stack 后
   widget 读取、compaction 摘要渲染非文本工具结果。
7. **平台/构建**：Windows spawn 拒绝超时重试；fetch_rg 下载 CDN 长时间故障的
   指数退避；CI 拆分 TUI 套件、缓存 vendored ripgrep；pytest addopts 改
   `--dist=worksteal` 且默认排除 `gc_calibration`；版本号 0.35.1→0.35.2。
8. 环境：`.python-version` 无变化（仍 3.14.10）；`uv.lock` 仅本项目版本行变化；
   vendored ripgrep 版本键无变化。

## 用户场景

1. 内部用户获得上游 0.35.2 的修复与新特性（会话全局搜索、整稿提示词编辑、
   skills 两层资源、MCP 重连、kernel 序列化修复等 38 提交内容）。
2. 开发者后续定制开发基于新基线，降低三层冲突累积债务。

## 验收标准

- [ ] merge 后 `gen_customizations.py --strict` 0 error / 0 warning；预期登记口径
      109 行 / 150 marker / 7 退役不变（若有实证增删，须同步登记并重签 design）。
- [ ] runbook §4 验证矩阵全绿：fork-full（`verify.py --full`，CodeBuddy 环境配方）、
      定制四门、R2/R3 以新 merge-base（预期 `2fd777f`）、ruff/format、ty 三平台。
- [ ] 行为锚定测试 `aixcoding/tests/diagnostics/test_panel_anchor.py` 绿。
- [ ] i18n 管线全通（extract → update → compile → check）；4 个借壳 key（C027）存活。
- [ ] 冲突解逐点核对：`test_program_status_lifecycle.py` 品牌常量适配后整文件通查
      无遗漏 `iCode` 断言，C079–C081 marker 计数保持 3。
- [ ] UPGRADE-RUNBOOK.md 头部「当前基线」节更新：上游版本 → 0.35.2、升级完成日期。
- [ ] 手册解耦口径留痕：升级批次不同步 manual 内容，`BUNDLED_DOCS_PATH`、
      `BUNDLED_DOCS_PREFIX` 与 force-include 目标三方一致（机制核对，非内容对账）；
      手册跟进作为独立事项移交。
- [ ] 升级决策清单（冲突点全清单+处理意见、定制化改变清单、淘汰检查逐组结论）
      已产出，全部决策经责任人裁决并留痕 verification.md。
- [ ] TUI 冒烟：`uv run aixcoding-cli` 启动正常，F6 可见 aixcoding tab，登录徽标/命令可用，
      F4 模型管理保持禁用（catalog 定制预期）。
- [ ] PR 双 CI（aixcoding-tests.yml + 上游 ci.yml 桥接）绿。

## 开放问题

- 无（merge 目标 ref 与手册解耦口径均已裁决）。

## 升级前基线状态（2026-11-11 实测）

- 工作树当时干净，`main_aixcoding_cli` 与 origin 同步（`d52626f1`）；
- 定制测试：**629 passed / 51 skipped / 0 failed**（117.83s，无 guard symlink 环境性失败）；
- `check_docs --closure`：OK（24 ADR / 38 design / 37 self-review；时点 = 本批次目录
  创建前。批次六件套齐备前 closure 红为预期态，收尾复跑绿后再开 PR）；
- `gen_customizations --strict`：**109 登记行 / 150 marker / 7 退役，0 error / 0 warning**。
