# ADR-0001：定制测试独立收集于 `aixcoding/tests/`

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-22
- 确认意见：实际测试验证过，可行

## 背景

定制测试的落点有两个候选：仓库根 `aixcoding/tests/`（独立收集，显式运行）或上游 `tests/` 树内（如 `tests/aixcoding/`，随默认收集）。历史上两种模式曾并存：登录改造测试在 `tests/app/aixcoding/`（11 个文件，随上游 CI 收集），telemetry 测试在 `aixcoding/tests/`（自建 conftest，显式运行）。

## 决策

统一到 `aixcoding/tests/`，上游 `tests/` 树内零定制文件；CI 执行点为独立 workflow `aixcoding-tests.yml`。

## 理由

规范 §1 的核心逻辑：定制测试是升级时**语义冲突的唯一检测器**，由此推出核心原则——**检测器不能与被检测对象共享故障域**。具体风险均有实证：

1. **隐式行为继承**：`tests/` 内的定制测试自动继承上游 `tests/conftest.py` 全部 autouse fixture 与 pytest 配置（markers/timeout/xdist/asyncio_mode）。上游升级改这些时定制测试行为被动变化，且变化在升级 diff 里不可见（diff 在上游文件里）。升级后定制测试红了，分不清"定制功能真坏了"还是"上游测试设施变了"——信号被污染。
2. **CI 分片裹挟**：`ci.yml` 各分片 `pytest_args` 显式列路径配 `--ignore`，且分片被 `tests/architecture/test_ci_test_partitions.py` 钉住、上游持续在调。上游重组 `tests/` 时定制测试可能被静默漏出 CI。
3. **升级 diff 甄别**：上游 `tests/` 高频变动，定制文件混在其中增加甄别成本；`aixcoding/` 在上游不存在，diff 天然干净。
4. **R2 永久例外状态**：`tests/` 视同上游源码，定制测试放进去则每次新增文件都是对上游树的侵入。

## 否决的备选

- **`tests/aixcoding/`（随默认收集）**：优点是自动进 CI、复用 `tests/support/` 设施、符合"项目唯一测试树"直觉。被否决：上述四条风险压倒收益；"执行可靠性"的正解是显式管道（独立 workflow + 标准自检命令），而非"住进 tests/ 被默认管道顺带跑到"。对上游设施的实际依赖经核查极浅（唯一跨目录 import 是 `tests.support.waiting.wait_until` 一处，复制即可），迁移成本可忽略。

## 后果

- 定制测试须自建 conftest（已验证约 100 行实现等价 config-dir 隔离）；
- CI 需要（并有）独立执行点；
- 上游 `tests/support/` 设施只可阅读、复制，不可 import。（现行规则以 DEVELOPMENT.md §9 为准；本文为决策时点快照。）

> **修订注记**（2026-11-01，local-verify 批次联动；四轮外部 AI 评审处置后口径校准，
> 决策结论不变——独立收集/独立门/不 import 上游设施三条均维持）：
> ① 本文中"唯一检测器"按规范 §1 语境理解为"专门的**自动**语义回归套件"——与治理工具
> （R2/R3/登记器）、上游测试、升级冲突分析、人工冒烟互补，不宣称唯一覆盖能力；
> ② 后果节"约 100 行实现等价 config-dir 隔离"表述超前于实现：实际以**测试内显式注入为主
> 范式**（`config_dir=tmp_path` + `MemoryBackend()`），顶层 conftest 为 sys.path + 通用
> fixtures，窄域 autouse（auth/conftest.py）为后续批次的防呆补充——隔离是有的，
> "conftest 等价物"的归因不准确；
> ③ 本地验收入口语义（local-verify 批次落地）：`aixcoding/tools/verify.py` 为统一入口
> （--smart 无条件双跑 / --full fork-full），定制套件从"须记得另跑"升级为入口内与上游
> 套件平级的执行单元——本决策"显式管道"路线的延伸，非推翻。
