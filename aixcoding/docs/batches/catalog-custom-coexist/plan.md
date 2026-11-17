# 计划：后端同步模型与自定义模型共存

> 活文档：随时更新、不签认。

**双 AI 自审通过（0 blocker）、findings 收敛、closure 全绿**（2026-11-16）。
分支 `feat/catalog-custom-coexist` 基于 `feat/catalog-field-mapping`（责任人授权）。
`design.md` 已由责任人本人签认（施利利 / 已确认 / 2026-11-16）。责任人裁决：
字段 `synced_from_server`、ID 冲突后端覆盖 + 完成后告警、告警载体**仅 detail 日志**
（不做 TUI 主动提示）、内存快照保持机制但扩展内容、TUI 只读不变、**不依赖
`.catalog-state.json` 做来源判定**、**零上游改动**。
评审 0 blocker / 3 suggestion / 3 nit，责任人拍板 F2 改代码、F3 补用例、F4 同步文档，
F1 确认意见本人已填、F5/F6 不修留档；增量复审 103 passed。第二轮独立 peer review
F1–F6 全部 confirm、**R1 处置后 approve**：R1 修（快照按 server_ids 过滤）、R2 澄清
commit/PR 口径、R3/R4 留档；终态 104 passed。`self-review.md` 头部由责任人签认并填
确认意见（「知情确认」）；`check_docs.py --closure` 实测 OK。待办：按授权提交。

## 待办

- [x] 责任人裁决：不做 TUI 主动提示，仅 detail 日志（零上游）
- [x] 责任人本人签认 `design.md`（施利利 / 已确认 / 2026-11-16）
- [ ] 责任人裁决 ADR 判定结论（design §ADR 判定：倾向不出 ADR）
- [x] 责任人裁决双 AI 自审的评审 AI 归属（GLM-5.3-Flash，与开发 AI 不同源）
- [x] 实施：标记读写（`_write_profile` 注入 + 扫描判定），零上游
- [x] 实施：`apply_catalog` 删除范围按标记 + 冲突检测 + result 新字段
- [x] 实施：内存快照扩展（后端 + 自定义），保持零磁盘 IO
- [x] 实施：detail 日志覆盖告警（零上游，不做 TUI 提示）
- [x] 实施：契约测试（保留/删除/冲突/告警/快照/指纹/state）
- [x] 跑门禁全集并把证据追加到 `verification.md`
- [x] 双 AI 自审 → `self-review.md` 补评审记录（0 blocker、F1–F6 收敛）
- [x] `check_docs.py --closure` 实测 OK（exit 0）
- [x] 责任人本人填写 `self-review.md` 头部确认意见栏（F1，本人填「知情确认」）
- [x] 第二轮独立 peer review：R1 处置后 approve（R1 修、R2 澄清、R3/R4 留档）
- [ ] 按责任人逐条授权提交 / 建 PR

## 挂起事项

- **不依赖 state**：判定只用模型 YAML 的 `synced_from_server`；
  `.catalog-state.json` 与 `profile_ids` 语义、内容均不改。
- **loader 不感知**：`read_profile_mapping` 忽略未知键是上游既有行为，
  契约测试钉死，不改 `schema.py` / `loader.py`。
- **升级一次性告警**：旧版无标记 YAML 首同步若 id 冲突会覆盖 + 告警，
  已写入 requirements 场景 4，责任人接受。
- **closure 草案期**：签认前 `check_docs.py --closure` 因草案禁入报错是
  正常中间态；默认模式 `check_docs.py` 应通过。不得由 AI 代填签认绕过。
