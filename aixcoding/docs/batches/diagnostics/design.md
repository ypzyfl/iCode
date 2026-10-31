# 设计：本地诊断包（aixcoding diagnostics）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认。校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-31
- 确认意见：确认退役 launcher / crash / snapshot 三组件

## 方案概述

定制层自有的本地诊断设施，三组件，全部落 `src/chrys/aixcoding/diagnostics/`：

```
~/.chrys/aixcoding.toml ──读取(tomllib,只读)──▶ 配置解析 config.py
                                                   │
     ┌─────────────────────────────────────────────┼──────────────────────────┐
     ▼                                             ▼                          ▼
 logging_support.py                          crash.py                     snapshot.py
 logger 工厂「aixcoding.*」命名空间            faulthandler + sys/          启动环境快照
 propagate = !tui.panel                       threading.excepthook         （版本/平台/开关，脱敏）
 + RotatingFileHandler（落盘恒开）            + atexit 兜底，写会话目录      崩溃时随 crash 归档
     │
     └─ propagate=True 且 tui.panel=true 时冒泡到 root → 上游 _TuiLogHandler
        → F6 日志查看器独立「aixcoding」tab（需 R2 一行白名单）
```

启用方式：**配置文件，非环境变量**（负责人明确要求：启动前可手动修改、重启生效）。

配置层定位：`~/.chrys/aixcoding.toml` 的解析器（`config.py`）是**定制层共享配置基建**——
诊断包是第一个消费者，未来任何定制功能的"启动前手动可改设置"均扩展此文件，不另建配置。

崩溃收集与环境快照经 `python -m chrys.aixcoding.diagnostics.launcher` 使用（装钩子后调上游
`chrys.app.cli.app:main`），零上游文件改动；日志组件谁 import 谁生效，不依赖 launcher。

## 备选方案对比

| 方案 | 优点 | 缺点 | 升级冲突面（文件数×行数×耦合度，R1） | 结论 |
|---|---|---|---|---|
| 日志：独立机制（自建日志库） | 完全自主 | 重复趟轮转/async/线程安全坑；丢 OTel instrumentation-logging 桥接红利；双体系认知负担 | 0 文件（但自建库维护成本永久） | 否 |
| **日志：独立通道（标准 logging 子树）** | 四项需求（分离/受众/时机/实现自由）全满足；零新依赖 | 无实质缺点 | 0 文件 | **采用** |
| 配置：寄生上游 `settings.yaml` | 单一配置入口 | 上游 `known_keys` 白名单（`specs_by_field(Settings)` 字段声明）将我方键判为 strangers（设置面板告警）；扩白名单=改上游 Settings 字段声明 | 1 文件×大量行 | 否 |
| **配置：独立 `~/.chrys/aixcoding.toml`** | 上游零感知；tomllib 标准库只读 | 多一个文件 | 0 文件 | **采用** |
| 面板：转发 handler（自写 handler 调上游单例） | 只进面板不进上游 debug 文件 | 依赖上游私有单例；自建组件多 | 0 文件（但私有 API 耦合） | 否 |
| **面板：propagate 切换** | 零自建组件；配置控制即 logger 属性 | panel=true 时记录也进上游 debug 文件（全量调试视图，合理行为） | 1 文件×1 行（见 R2 表） | **采用** |

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记注释位置 |
|---|---|---|---|
| `src/chrys/app/tui/screens/logs/screen.py` | `MODULE_ORDER` 元组增加 `"aixcoding"` 项（`MODULE_WHITELIST` 派生自动跟随；F6 tab 由 `for module in MODULE_ORDER` 自动生成） | 1 | 该行行尾 |
| `tests/architecture/test_layering.py` | ① `TIER_ORDER` 注册 `"aixcoding": 1`（新一级子包 tier 登记，1=只准依赖 foundation/kernel，对应 R9/DIRECTORY tier 表；上游 workflows facade 同型先例）；② 新增 `_DAG_EDGE_ALLOWLIST`（仿既有 kernel-private allowlist 模式，含 stale-entry 防漂移检测）登记 `launcher.py → chrys.app.cli.app` 一条边（本表下方登记预告已载明的 R9 入口豁免）。**实施中补充**（2026-10-25 负责人批准）：架构 DAG 为白名单制，新子包必须注册，规范 R9 条文③与 DIRECTORY tier 表预期此登记，设计初稿漏列 | 约 20 | 两处改动行尾 |

R1 自查：业务逻辑全部外置 `src/chrys/aixcoding/diagnostics/`；接线点仅白名单一行，无法更少。
崩溃收集/环境快照零接线（launcher 包装，`python -m` 运行）；pyproject entry point 为可选增强，
如需另行报批。**实施前按 R2 流程向负责人确认本表。**

已知取舍（接受）：`MODULE_ORDER` 加项后 aixcoding tab 常驻 F6（即使 `panel=false` 显示空态，
与 httpx 无请求时的空 tab 行为一致）；隐藏空 tab 需改上游 `compose()`，扩权不值。

## 对上游隐式行为的假设

| 上游行为 | 我方依赖方式 | 假设失效时的表现 |
|---|---|---|
| `_TuiLogHandler` 挂 root、按 `record.name.split(".")[0]` 对照白名单过滤 | `propagate=True` 时记录冒泡送达 root handler | 面板无 aixcoding 内容（降级为纯落盘，无错误） |
| `install_log_handler()` 幂等、由 app.py 启动时调用 | 不自行安装，仅依赖其已存在 | headless/测试进程无 handler，同样降级为纯落盘 |
| headless `NullHandler` 挂 root | 不影响子树自挂 FileHandler（handler 挂载与 root 无关） | 无（logging 语义保证） |
| 上游不感知 `~/.chrys/aixcoding.toml`（同目录陌生文件） | 独立读取 | 极小概率：上游目录管理动作影响该文件（届时配置失效→日志关闭，fail-safe） |
| 上游 `settings.yaml` 的 `known_keys` 白名单机制 | 不寄生，故无依赖 | 无 |

## 定制点登记预告

> 2026-10-30 更新：launcher / crash / snapshot 三组件已退役（ADR-0013，批次 aixcoding/docs/batches/launcher-retirement/）——登记行删除，现存组件仅 config 与 logging_support。
> 2026-10-31 点级化（customization-registry 批次）：原包内两文件行（config.py / logging_support.py）语义并入 C007 anchor；自有资产清单归 DIRECTORY.md。

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C007 | src/chrys/app/tui/screens/logs/screen.py | AIxCoding diagnostics: F6 tab | | `~/.chrys/` 目录约定（`get_platform().config_dir` 同源）+ `logging` 标准机制 + `MODULE_ORDER`（R2 一行）；支撑组件 config.py / logging_support.py（ADR-0013 收敛后存续两件） | 低（面板）/零（落盘） | 〔上游等价〕上游日志面板原生支持第三方模块分层展示（MODULE_ORDER 类机制）且可承载定制层日志 |

## 风险与最坏情况

- 决策错了会怎样：「独立通道」若未来不够（需要事件流/跨进程语义），标准 logging 记录可无损
  迁移到任何新机制（记录产生与传输解耦）；R2 一行回滚 = 删该行，面板消失、落盘不受影响。
- 配置错误：解析失败 → 诊断功能整体关闭（fail-safe），不影响上游任何行为。
- 最坏情况：launcher 与上游入口签名漂移 → launcher 报错退出，开发者回退直接 `icode` 命令。

## ADR 判定

「策略层独立、机制层复用」是跨特性原则（未来 metrics/tracing 同理：独立开关与目的地，
走 OTel SDK 多 provider，不自建 SDK）。实施时按 DEVELOPMENT.md §6 判定；若四问触发，
以 ADR-0009 固化该原则，本文引用之。崩溃收集与环境快照的组件级细化（输出格式、保留策略、
脱敏清单）在实施 design 定稿时补充。
