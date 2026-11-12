# aixcoding —— AIxCoding 定制专区（开发资产与分发物料）

> **基线**：2026-10-25 起在新分支 `main_aixcoding_cli`（上游 0.31.0 干净基线）重建；旧分支 `main_aixcoding_cli_0.28.0_final` 资产的迁入映射见 `docs/batches/restructure/plan.md`，后续迁移项由责任人自行跟踪。

本目录承载 iCode-fork 的**全部定制开发资产**（文档、测试、mock、开发工具）、**定制用户使用手册源**（`manual/`）与**随制品分发物料**（安装器脚本、用户安装手册，`release/`，ADR-0020）。其中 `manual/` 经 `force-include` 捆绑进 wheel，其余目录不进 wheel。
进 wheel 的定制产品代码按 tier 落位 `src/chrys/{tier}/aixcoding/`（ADR-0011）。

## 结构一图

```
aixcoding/
├── docs/          # standards/（规范族+全局 ADR+模板）、madr/（轻量决策记录）、batches/<批次名>/（全部批次/专项目录，ADR-0016/0024）
├── tests/         # 定制测试唯一落点（显式运行，见下）
├── mock/          # 自建 mock 专区（auth / update / model_catalog / telemetry）
├── manual/        # 定制用户使用手册源（zh-Hans / en / index.yaml；F8 手册，force-include 进 wheel）
├── release/       # 随制品分发物料（内网安装器脚本、用户安装手册；ADR-0020）
└── __init__.py    # 开发资产 import 命名空间锚点（不进 wheel）
```

## 速查

| 我要… | 去哪 / 怎么做 |
|---|---|
| 新增定制产品代码 | `src/chrys/{tier}/aixcoding/`（档位判据见规范 §3；先读 `docs/standards/DEVELOPMENT.md`） |
| 新增定制测试 | `aixcoding/tests/<特性>/` |
| 新增 mock | `aixcoding/mock/<服务名>/`（步骤见 `mock/README.md`；必须配契约测试） |
| 编辑定制用户使用手册 | `aixcoding/manual/`（双语 Markdown + `index.yaml`；勿改上游 `docs/`，构建经 force-include 捆绑） |
| 新增分发物料（安装器/安装手册） | `aixcoding/release/`（ADR-0020；随内网镜像分发，非开发过程消费） |
| 跑定制测试 | `uv run --extra all pytest aixcoding/tests -m "not integration and not gc_calibration"` |
| 查批次目录全景（不含无目录微改动） | `uv run python aixcoding/tools/docs_report.py`（按需只读、零写入） |
| 查定制点全景 / 升级地图 | `uv run python aixcoding/tools/gen_customizations.py --report`（实时对账，勿编辑不落盘） |
| 查硬规则（R1–R13） | `docs/standards/DEVELOPMENT.md` |
| 判定本次改动走全管线还是微改动豁免 | `docs/standards/DEVELOPMENT.md` §6（三条件全满足即豁免） |
| 查人机工作流（责任人五个检查点 + AI 执行流） | `docs/standards/DEVELOPMENT.md` §4 |
| **团队成员必读（我要做什么·一页）** | `docs/standards/TEAM-GUIDE.md` |
| 查目录细则（落点/蓝图/tier/命名） | `docs/standards/DIRECTORY.md` |
| 查"为什么这样定" | `docs/standards/adr/`（含被否决的备选）；小决策/决定不做查 `aixcoding/docs/madr/`（轻量决策记录） |
| 自审怎么做（作者，提 PR 前照做） | `docs/standards/SELF-REVIEW-HOWTO.md` |
| 评审怎么做（评审人，打开 PR 照做） | `docs/standards/PEER-REVIEW-HOWTO.md` |
| 新建功能文档 | 从 `docs/standards/templates/` 复制骨架（requirements/design/test-plan/plan/verification/self-review/adr） |
| 签认文档（R10 责任人本人） | 编辑文档头部字段：状态→已确认、填日期；AI 不得代填 |
| 校验文档闭环 | `uv run python aixcoding/tools/check_docs.py --closure`（签认、六件、ADR 引用与 plan 完成状态） |

无目录微改动查 [GitHub merged PR 视图](https://github.com/ypzyfl/iCode/pulls?q=is%3Apr+is%3Amerged)，按 PR 描述人工识别；docs_report 不统计此类改动。

## 历史备注

本目录曾含 `auth/`、`tui/` 产品代码并以顶层包身份进 wheel（2026-10-08 `f4f90f5`），曾名 `telemetry-mock/`、`doc/` 等混杂结构。2026-10-21 目录重组（见 `docs/batches/restructure/plan.md` 与 ADR-0002/0003）后定位收敛为纯开发资产；2026-11-05 起增设 `release/` 分发物料维度（ADR-0020，internal-installer 批次）。
