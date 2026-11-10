# 任务清单：并行批次编号与文档热点治理（parallel-batch-governance）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

工具、测试、规范与根文档原子切换已实施，INDEX/ROADMAP 已物理删除，豁免清单经责任人确认迁至 `standards/closure-exemptions.toml`。GLM-5.3 实施评审与增量复审收敛，S1 已修正；周彬已于 2026-11-10 签认本批 self-review。责任人后续要求补齐所有该跑测试，统一 `verify.py --smart` 已实际执行：定制 605 passed / 51 skipped，上游 tests 35854 passed / 737 skipped，architecture 1247 passed / 3 skipped / 1 deselected，Summary 均 PASSED。closure、strict、ruff/format、import 边界、R2/R3、guard 验证与 mock + TUI 手动冒烟全绿。当前只待提交、PR 与 AIxCoding Tests / Upstream CI 双 CI。

## 待办

- [x] 核查 C###、ADR、INDEX、ROADMAP 的现行规范和工具耦合。
- [x] 按责任人最新裁决明确 ROADMAP 随本批物理删除、迁移项自行跟踪及活引用清理清单。
- [x] 比较 INDEX 人工单写、薄入口只读聚合、分布元数据和完全删除方案；裁决采用完全删除 + `docs_report.py` 按需视图。
- [x] 起草 requirements、design、plan 与 ADR-0024。
- [x] 按总目标补入 M0/M1/M2 冲突分级、新 ADR 语义 ID 和 ID-only 机械修复预授权。
- [x] 补入文档闭环门禁四项机制、存量缺口封闭清单与 guard-switches 修复验收项。
- [x] 按交叉评审补齐确定性改号与只读语义差异校验、收窄 plan 结构化检查、明确清单只减不增及 R13 联动，并修正实施顺序与引用计数。
- [x] 同步 `origin/main_aixcoding_cli@9d824cb5`，INDEX 同时保留 user-manual 与本批登记行，并复核新增批次六件完整、存量豁免清单无需变化；评审发现 llm-keyless-sdk-auth 漏登记后已按现行规则补登，作为人工登记无门禁必漏的实证。
- [x] 原交叉评审 AI 完成增量复审，事实核对 12 项全部通过，新增 F1-F5 五项建议。
- [x] 处理 F1-F5：修正 INDEX 描述、补登 llm-keyless 并记录漏登记实证、预留 ADR-0023/0024、明确微改动增量分流、澄清 pull_request closure 边界。
- [x] 原评审 AI 确认 F1-F5 全部修复到位、零阻塞；N1/N2 收尾事项已同步。
- [x] 责任人裁决 design 末节七项重点选择，并于 2026-11-10 签认 design（无特别意见）。
- [x] 责任人本人于 2026-11-10 签认 ADR-0024（无特别意见）。
- [x] 编制 test-plan，覆盖双格式 ID、M0/M1/M2 场景、closure 四项门禁、INDEX/ROADMAP 物理删除与引用清理、导航零写入/防复用、有目录微改动纳入/无目录微改动排除的边界，以及新增缺件微改动目录 closure 失败、无目录豁免不触发六件门禁的增量分流。
- [x] 按签认范围实施工具、测试、规范和根文档原子切换；物理删除 INDEX 与 ROADMAP，README 速查表加入批次目录全景 / 定制点全景两条相邻命令入口并删除旧路线入口，注明无目录微改动查 GitHub merged PR。
- [x] 实施 guard-switches 存量修复：ADR-0023 迁移、3 个文件旧引用与 H1 更新、verification 补做和 plan 更正均完成；GLM-5.3 第二 AI 评审与责任人签认已完成，F1/F3 按责任人裁决修复。
- [ ] 最终 closure、Smart Test、完整定制/上游/架构套件、strict、ruff/format、import 边界、R2/R3 和 guard 验证均已通过；待提交与 PR 后确认 AIxCoding Tests / Upstream CI 双 CI。
- [x] GLM-5.3 实施评审与增量复审均完成，F1-F5 已处置、S1 已修正、评审收敛；周彬已于 2026-11-10 签认本批 self-review。
- [x] 按责任人 2026-11-10 补充要求，以 user-manual 批次为依据同步 README、DIRECTORY、DEVELOPMENT 与 UPGRADE-RUNBOOK 的 `manual/` 落点、wheel 例外、安装/使用手册区分和升级对账义务。

## 挂起与备忘

- INDEX 与 ROADMAP 均随本批物理删除，不保留退役标记、冻结档案或重定向；ROADMAP 不等完整验收或旧分支归档，迁移项由责任人自行跟踪，历史内容从 Git 获取。
- 批次 design 的 R2 审批、现役登记和 tombstone 是持续效力资产，不随 ROADMAP 删除；历史批次和 ADR 中的当时叙述不批量改写，失效路径查 Git 历史。
- docs_report 只承诺批次目录全景：有目录的微改动照常纳入，无目录微改动查 GitHub merged PR，不补 `micro/`、不联网、不做微改动分类或计数。规则生效后，§6 豁免微改动不新建 batches 目录；需要目录即走完整管线六件，新增缺件微改动目录必须 closure 失败，不逐次新增 ADR 豁免。
- ADR-0024 自身保留起草时的旧数字格式；guard-switches 决策按时间顺序迁为全局 ADR-0023，ADR-0023/0024 是语义 ID 规则生效前最后两个旧数字 ADR；0023/0024 已由本批预留，实施窗口内并行批次不得占用；此后新 ADR 使用语义 ID，check_docs 将 `batches/*/adr/` 判为位置错误。
- ID-only 机械修复的免重复签认仅限 design 明确的 M1 边界；任何行为、决策、登记语义字段或 R2 变化仍须停等。
- 存量缺口封闭清单基于 `origin/main_aixcoding_cli@95e23add`，运行时落 `standards/closure-exemptions.toml`，常态只减不增；新增/扩大含基线漏项均须另出 ADR 并签认。2026-11-10 已同步并复核 `9d824cb5`：新增 `llm-keyless-sdk-auth`、`user-manual` 六件完整，清单保持不变；后续实施前如远端再更新仍需复核，如需扩大清单不得自行加入。
- closure 在 pull_request（含特性分支 PR）及 push 到 main_aixcoding_cli 时执行；本地手动默认模式允许草案，但 PR 不使用宽模式。
- guard-switches ADR 补签与 self-review 签认必须由责任人本人编辑，AI 只能准备草案与验证证据，不得代填或倒填日期。
