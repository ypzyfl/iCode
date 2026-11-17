# 任务清单：后端同步模型与自定义模型共存

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

交付评审（ypzyfl，2026-11-17）**Approve**：两提交全链路通过，3 findings 处置
完毕（finding-1 design 措辞已纠、finding-2 留档、finding-3 顺手修），
`--closure` OK。剩余：责任人更新 design 确认意见（补 finding-1/2 处置）→
追加处置小提交 → 合并。

## 待办

- [x] 责任人审阅并签认 design.md（2026-11-17）
- [x] 实现：`src/chrys/service/aixcoding/models/catalog.py`（标记契约 / 探针三态 /
      stem 判定 / 升级清空 / 内存快照过滤）
- [x] 实现：`aixcoding/tests/catalog/test_catalog_sync.py` 新增 15 个契约/锚定用例
- [x] 验证：Smart Test + 定制套件 + ruff 双检 + `gen_customizations --strict` +
      ty 三平台，证据见 verification.md
- [x] 双 AI 评审第 1 轮（Deepseek-V4.1-Flash）：3 blocker + 1 签认 blocker + 5 次要
- [x] 评审修复轮：B1（探针解码对齐 + 失败/否决日志）、B2（完整文件名判定）、
      B3（docstring 对齐）、S2（非 vacuous 指纹测试）、S5（需求措辞）；
      S1/S3/S4 留档/申报
- [x] 三平台文件操作审计 + S6 修复（normcase 判定口径 + 平台分支测试）
- [x] 双 AI 评审第 2 轮（Deepseek-V4.1-Flash）：B1–B5/S2/S5 收敛，S6 引入 B5；
      r1/r2/r4 修复、r3 留档
- [x] B4：责任人补填 self-review.md 头部（2026-11-17）
- [x] `check_docs --closure` 转绿
- [ ] 评审 AI 对 B5 修复行做最小复审确认（收敛判断的最后一项）
- [ ] 责任人更新 design.md 确认意见，覆盖 B1/B2/S6/B5/r2 全部修正（AI 不代填）
- [ ] 测试全绿后做第二个提交（整合提交，git 写操作逐条授权）

## 挂起与备忘

- 旧分支 `feat/catalog-custom-coexist`（tip `1eb3c099`）保留作内容索引；旧轮次
  评审记录（F1–F6、R1–R9）已全部吸收进本 design，不再引用旧提交哈希。
- 本地坏文件 `~/.chrys/models/openai-gpt-4o-mini2.yaml` 未删（用户数据，未经
  授权不删）；修复后应按自定义保留、不中断同步。
- 历史风险留档：纯用户目录（全无标记）会被升级清空误删，责任人已明确接受
  （requirements 场景 4 / design 风险节）。
