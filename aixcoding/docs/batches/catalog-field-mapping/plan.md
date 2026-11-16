# 任务清单：catalog-field-mapping

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**双 AI 自审通过（0 blocker）、责任人签认完成、closure 全绿**（2026-11-16）。
`design.md` 已由责任人本人签认（施利利 / 已确认 / 2026-11-14）；按
DEVELOPMENT.md §4.1 完成代码、mock 数据、契约测试与 README 改动，门禁全集证据见
`verification.md`。评审 findings F1–F5 已逐条拍板收敛（F1/F2/F5 修、F3 保留、
F4 不修留档），增量复审 91 passed。`self-review.md` 已由责任人本人签认
（施利利 / 已确认 / 2026-11-16）；`check_docs.py --closure` 实测 `OK`（exit 0），
全部治理门禁收敛。剩余流程动作仅在责任人授权后进行 git 提交 / 建 PR。

## 待办

- [x] 责任人本人签认 `design.md`（施利利 / 已确认 / 2026-11-14）
- [ ] 责任人裁决 ADR 判定结论（design §ADR 判定：倾向不出 ADR；
      若认定字段映射表＝对外契约，须出语义 ADR 并签认）
- [ ] 责任人确认批次目录名 `catalog-field-mapping` 是否保留
- [ ] 责任人裁决双 AI 自审的评审 AI 归属（须与开发 AI 不同源；
      HOWTO ② 为建议性口径）
- [x] 实施：`catalog.py` 加嵌套映射表（+18 行），未改 `parse_catalog()` /
      `_positive_int()` / `item` 既有键
- [x] 实施：`config_new.json` 补三组嵌套块（`provider`、`aa` 原样保留）
- [x] 实施：契约测试（转换层 + 干扰项 + 异常降级 + 落盘 / loader 读回）
- [x] 实施：mock README 补字段映射说明，并修正错误路径与失效引用
- [x] 跑门禁全集并把证据追加到 `verification.md`
- [x] 双 AI 自审 → `self-review.md` 补评审记录（0 blocker、F1–F5 收敛）
- [x] 责任人本人签认 `self-review.md` 头部（施利利 / 已确认 / 2026-11-16；AI 未代填）
- [x] `check_docs.py --closure` 实测 OK（exit 0）
- [ ] 按责任人逐条授权提交 / 建 PR

## 挂起与备忘

- **closure 当前态**：责任人 2026-11-16 本人签认 `self-review.md` 后，
  `check_docs.py --closure` 实测 `OK`（exit 0，27 ADR / 46 design /
  45 self-review），默认模式 `check_docs.py` 同绿；AI 全程未代填签认。
- **评审偏差处置**：`parse_catalog()` 未校验三个新字段类型，与 design
  「风险与最坏情况」首段的偏差经 F2 拍板已在 design 原位加注记
  （不触发重签），事实与证据见 `verification.md` 偏差节；F1 另补 null
  子键落盘回退默认的契约断言，评审 0 blocker 收敛。
- **不引用**：本批不引用 `catalog-sync/` 下那份将被移除的交接说明；
  目标契约已内联冻结于 `design.md`，自洽可查。
- **零上游**：R2 清单为空、R3 无 marker、R13 零新增豁免；
  `gen_customizations.py --strict` 无登记义务。
- **范围边界**：不改白名单式透传、不做请求参数日志、不加 `reasoning` 字段、
  不碰 `schema.py`；iCode 侧 13 个后端不下发的字段保持本地默认。
- **验收口径**：当前 `ModelProfile.stream` 默认值为 `True`；本批不引入
  请求日志，不以 `stream: false` 的日志期望值当验收依据。
- 既有两个契约测试因 import 不存在的上游模块而自动 skip，
  不作为本批验收依据，也不为其改断言或加豁免（R13）。
