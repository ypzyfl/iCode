# 需求：检查域模型与定制域按需触发（compliance / aixcoding-tests / guard-deploy / upstream）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。
>
> 决议留痕（2026-11-12，责任人裁决 + 三轮外部 AI 讨论收敛）：放弃数字层号（L0/L1/L2 绑死
> 触发策略与职责域两个正交维度），定案**四检查域 + 两聚合 required check** 模型；域名描述
> **被运行的检查套件**，不描述只有哪个目录的改动才触发它；射程规则单点登记于分类器（域
> 集合输出、非互斥）；旧 ADR 数字层表述以四行映射表收尾。立项依据：PR #122 实测纯文档 PR
> 的 test+guard 恒跑约 3 分钟（关键路径 Windows 83s+排队），其真正射程只有 compliance（26s）。
> 讨论材料：`fork/temp/2026-11-12-ci-gate-domains-naming-and-matrix.md` 及其评审结论。

## 背景与问题

upstream-ci-tiering 批次（PR #121/#122，已合并）完成上游回归按需触发后，`AIxCoding Tests`
里的 `test`（双 OS 全量 pytest）与 `guard`（三 OS 部署验证）仍恒跑。本批把两者按各自射程
独立触发，并把整个门禁体系表述为四检查域：

| 检查域 | 内容 | 触发策略 | 聚合去向 |
|---|---|---|---|
| `compliance` | govern（ruff/format/ty 三平台/compileall/check_docs --closure/import 边界/定制注册表/R2R3） | 恒跑 | `AIxCoding quality gate` |
| `aixcoding-tests` | `test` job：`pytest aixcoding/tests` 双 OS | 按射程 | `AIxCoding quality gate` |
| `guard-deploy` | `guard` job：真实安装 guard 规则包 → stdlib 自检 → MANUAL_TESTS 语料回放，三 OS | 按射程 | `AIxCoding quality gate` |
| `upstream` | 桥接复用上游 `ci.yml` 全套（已落地，本批不动） | 按影响面 | `AIxCoding upstream gate` |

### 已核实的射程事实（代码级依据，约束前提）

- `aixcoding/tests/guard/guard_pack_selftest.py:28` 导入 `aixcoding.tools.guard_install_merge`，
  `verify_guard_deployed.py` 以 `batches/guard-hooks/rule-pack/MANUAL_TESTS.md` 为回放语料
  ——独立安装合并工具与语料文档均属 guard 部署链路。
- `src/chrys/kernel/aixcoding/guard/guard_install.py:42` 导入 `chrys.foundation.platform`
  ——guard 安装链路依赖上游平台代码，上游源码变更可能破坏其部署。
- guard job 自身执行 `.python-version` 解释器配置 + `uv sync`——测试环境文件属其运行环境射程。
- `aixcoding/tests/conftest.py` 不复用上游 `tests/support`——上游测试变更不触发定制域有据。
- `aixcoding-tests.yml` 触发含 push 至 `main_aixcoding_cli`（push 恒全跑=每次合并的全量兜底）。

## 目标与非目标

- 目标：
  1. **射程分类扩展**：`ci_impact.py` 新增判定函数（单实现延续），输出域集合（非互斥）：
     - `aixcoding-tests` 射程：`aixcoding/tests/**`、`aixcoding/mock/**`、
       `src/chrys/{tier}/aixcoding/**`、测试环境文件、**`aixcoding/tools/**` 可执行代码**
       （纯文档/人工资产除外）、**上游产品源码**（定制层 import 上游符号，upstream 套件
       不感知定制层断裂）；
     - `guard-deploy` 射程：`src/chrys/kernel/aixcoding/guard/**`、`aixcoding/tests/guard/**`、
       `aixcoding/tools/guard_install_merge.py`、**MANUAL_TESTS.md 语料**、测试环境文件
       （guard job 运行环境）、**上游产品源码**（platform 依赖已核实，不维护上游依赖细表）；
     - 环境文件与上游源码为**多域命中**（域集合输出）；纯文档除"文档即验证输入"例外
       （共 9 文件，design R7 + R11）外不触发任何按需域。
  2. **按需触发**：`aixcoding-tests.yml` 前置 filter job（python3≥3.14 版本门限探测同款）+
     `test`/`guard` 各自条件触发；域名与 job 对应关系如上表。
  3. **FORCE 防自裁**（判定基础设施变更从严）：`aixcoding-tests.yml` 自身、`ci_impact.py`、
     `_common.py` → 定制双域全跑（描述为判定基础设施从严，非对 workflow 功能的验证）。
  4. **未知路径全域 fail-closed**：未匹配任何规则的路径 → 三个按需域全跑——upstream 全量
     本就是关键路径（11-23 分钟），并行加跑定制双域（约 3 分钟）**不增加 PR 总等待**，却防
     新目录/新资产类型漏判；push-to-main 全跑是合并后兜底，不能替代 PR 阶段预防。
  5. **push 路径**：push 至主干恒全跑（现状延续）；nightly/dispatch 覆盖全部三个按需域
     （custom-test/guard 成本极低；收益除无合并空窗外，还包括 runner 镜像/托管环境漂移、
     时间相关退化、push 验证失败或取消后的独立复测；nightly 与 push 均为合并后兜底，不替代
     PR 保守触发）。
  6. **gate 状态机扩展**：`AIxCoding quality gate` 接受 `(域未命中 ∧ job skipped)` 合法态，
     其余 fail-closed；gate 输出列出各域 success/skipped 及跳过原因（聚合门全绿可知实际
     跑了什么）；required check 名与分支保护零改动。
  7. **文档联动**：新 ADR（检查域模型替代数字分层术语，四行映射表：L0→compliance、
     L1-test→aixcoding-tests、L1-guard→guard-deploy、L2→upstream；"两个 required check
     名称及实现机制不变"）+ DIRECTORY §7 改口径 + 批次六件 + 分类器测试矩阵。
- 非目标：
  - `upstream` 域与桥接 workflow 任何改动（已闭环；其 FORCE/DOC/CUSTOM/默认规则不变）。
  - `compliance` 按需化（恒跑是定义）。
  - 各域内部再细分（OS 矩阵裁剪、测试目录级选择）。
  - 上游文件改动、新增第三方依赖。

## 用户场景

1. **纯文档 PR**（手册/文档回填；**文档即验证输入的例外**——MANUAL_TESTS.md、根 `AGENTS.md`、
   `UPGRADE-RUNBOOK.md` 被静态契约测试消费，属 aixcoding-tests 射程，不在此列）：仅
   compliance + 两 gate，总等待约 1 分钟。
2. **仅测试改动 PR**：compliance + aixcoding-tests（guard-deploy 不跑，除非触及
   `aixcoding/tests/guard/`）。
3. **guard 链路改动 PR**（规则包/安装器/语料）：compliance + aixcoding-tests + guard-deploy
   （多域命中）。
4. **定制产品代码 PR**（复刻 catalog-auto-sync 形态）：compliance + aixcoding-tests，
   upstream 仍跳过（两层判定互不耦合）。
5. **追上游升级 PR**（上游源码变更）：四域全跑——upstream 全量为关键路径，定制双域并行
   加跑不增加总等待，消除定制层与 guard 部署的跨层断裂漏判。

## 验收标准

- [ ] 纯文档 PR：`test`/`guard` 均 skipped，govern 照跑，`AIxCoding quality gate` 直绿可合并，
      gate 输出可见各域 success/skipped 与跳过原因。
- [ ] 射程矩阵逐格行为（含多域命中：`aixcoding/tests/guard/`、`guard_install_merge.py`、
      环境文件、上游源码）与目标 1 一致，分类器测试矩阵全案例绿。
- [ ] MANUAL_TESTS.md 改动触发 guard-deploy；"文档即验证输入"9 文件（AGENTS.md、
      UPGRADE-RUNBOOK.md、release/INSTALL.md、install-uninstall-support.md、publishing.md、
      rule-pack README/OPERATIONS/PORTING）改动触发 aixcoding-tests；scripts/上游 workflow
      落 R12 触发**定制双域**；其余纯文档不触发任何按需域。
- [ ] FORCE 命中（workflow 自身/分类器/_common）：定制双域全跑。
- [ ] 未知路径：三域全跑（fail-closed），有测试固定该行为。
- [ ] push 至主干：定制双域恒全跑；nightly/dispatch 覆盖三域。
- [ ] `ci_impact.py` 既有 upstream 判定与 38 例测试零回归。
- [ ] 真实纯文档 PR 端到端验证（三件套复现于定制双域）。
- [ ] 新 ADR 合并（含四行映射表）；DIRECTORY §7 与 upstream-ci-tiering 批次文档交叉引用；
      closure 转绿。

## 开放问题

- （已收敛，无遗留开放问题——三口径与五类射程反例均已定案入目标；guard-deploy 射程的
  精确文件清单在 design 以"分类器规则表"形式落盘，文档不复制清单。）
