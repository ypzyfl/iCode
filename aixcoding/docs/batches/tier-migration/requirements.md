# 需求：ADR-0011 存量定制包按 tier 回迁 kernel 档

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

ADR-0011（已签认 2026-10-27，PR #63）将定制代码落位规则由"单点 `src/chrys/aixcoding/`"改为
"按依赖落位 `src/chrys/{tier}/aixcoding/`"。存量 `auth/`、`diagnostics/` 两包仍在旧单点，
需回迁 `src/chrys/kernel/aixcoding/`。时机依据 ADR-0011 理由 4：tui/catalog 批次迁入前
auth 消费面处于历史最小，此后只增不减。

## 目标与非目标

- 目标：执行 ADR-0011 决策 3/4/5——两包 git mv 至 kernel 档、import 改写（包内相对化 +
  包外前缀替换）、上游还原（删 `TIER_ORDER` fork 键）、工具分类器跟进新路径形态、
  launcher 命令与活文档联动。
- 非目标：不迁入任何新功能（tui/catalog 等不在内）；不改两包任何逻辑（纯位置移动）；
  不改 ADR-0011 已定规则；不动签认/记录快照档（R8 留档）。

## 用户场景

无用户可见行为变化（内部结构改动）。开发者可感知差异仅两处：
- import 路径 `chrys.aixcoding.*` → `chrys.kernel.aixcoding.*`；
- launcher 命令变 `python -m chrys.kernel.aixcoding.diagnostics.launcher`。

## 验收标准

- [ ] 全库（活代码与活文档）无 `chrys.aixcoding` 旧前缀残留——R8 留档项除外
  （`mock/update/__init__.py:32` 随 update 批次、`ROADMAP.md:106-107` 随阶段三完成度、
  签认/记录快照档、ADR 快照）；
- [ ] `pytest tests/architecture` 绿（含 `TIER_ORDER` 键删除后分层判定、豁免边 Path 更新）；
- [ ] `pytest aixcoding/tests` 绿（14 文件前缀替换后全量通过，含工具自检 4 文件夹具更新）；
- [ ] `ty check` 绿（kernel 档新路径）；
- [ ] wheel 冒烟：`chrys.kernel.aixcoding` 在包内（hatchling `packages=["src/chrys"]` 递归覆盖）；
- [ ] `CUSTOMIZATIONS.md` 重新生成后路径列反映新落位。

## 开放问题

- 无。
