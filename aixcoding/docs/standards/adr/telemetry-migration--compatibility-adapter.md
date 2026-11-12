# ADR-telemetry-migration--compatibility-adapter：企业埋点保留旧报文并收敛引擎接线

- 责任人：兰荣达
- 状态：已确认
- 确认日期： 2026-11-12
- 确认意见：已确认

## 背景

0.28.0 企业埋点依赖模型请求发出时的数据、逐次写入快照和真实工具归属。升级后组栈和事件发布点已有变化。现网仍以旧报文统计，目标分支 0.35.2 需要保住这些语义。

## 决策

企业模块沿用 0.28.0 的报文结构、编码规则和上报端点。按事件边界从目标引擎采集，通过企业数据类型隔离上游。优先复用已有引擎事件和快照，只在现有出口缺字段或触发点时增加接线。模型请求继续在发送前搭载 `body.telemetry`。本地工具按 kernel 操作 ID 关联模型调用，托管工具在观察时捕获来源。正常和 GET 续读保留旧归属。失败和并发改用实际来源，来源缺失时省略三个关联字段并继续发送工具记录。

## 理由

纯 Hook、OTel 和网关适合提供旁路证据，不能共同保证逐次文件快照与旧请求关联。ACP 代理无法覆盖原生 TUI 执行，聚合 diff 也无法还原同一轮的中间修改。整体照搬旧补丁会保留已过时的分 provider 接线和旧事件布局。新版统一组栈点与现有工具事件可以缩小接触面。

## 后果

依赖上游内部事件、模型 middleware 和会话元数据的挂点须登记。每次升级按相同录制场景比较报文，并检查事件时序和关联。在上游提供等价公开接口且通过对拍后，才退役对应挂点。本次 R2 签认覆盖设计 §7 和逐行附件。实施验收包含字段、时序与归属对拍，以及一次跨版本适配成本演练。见 [迁移设计](../../batches/telemetry-migration/design.md) 和 [逐行审阅稿](../../batches/telemetry-migration/r2-review.md)。


## 2026-11-12 新增 R2 范围补充签认（非零 rollback 与后台保存竞态）

- 责任人：兰荣达
- 状态：已确认
- 确认日期：2026-11-12
- 确认范围（仅限本段列出的路径与目的）：
  - `src/chrys/orchestration/engine/session_lifecycle.py`
  - `src/chrys/orchestration/engine/rollback.py`
- 修法意图：在非零回滚中协调后台归属保存与快照替换：暂停新的后台保存，等待已有保存完成，替换快照并恢复后再开放。具体最小实现由实施代理判断。
- 确认意见：授权确认上述新增 R2 范围，用于该竞态的最小产品修复。本确认不包括等待清单新增或扩大项，也不扩大兼容适配决策的其他后果。

## 2026-11-12 新增 R2 范围补充签认（回滚修复的任务所有权与等待清单登记）

- 责任人：兰荣达
- 状态：已确认
- 确认日期：2026-11-12
- 确认范围（仅限本段列出的路径与目的，且仅覆盖本轮非零回滚修复所必需的登记）：
  - `tests/architecture/test_layering.py`：在 `test_background_tasks_have_declared_owners` 增加一条任务所有权记录，键为 `("session_lifecycle", "SessionLifecycle", "refresh_mutation_attribution")`，计数为 1。
  - `tests/architecture/trajectory_wait_manifest.json`：按 2026-11-12 15:08（上海时间）内存对账的实际候选写入文本差异 +6/−1（等待条目 2925→2928），仅限 `RollbackController.on_user_rollback`、`SessionLifecycle.pause_mutation_attribution_saves` 与 `SessionLifecycle.refresh_mutation_attribution` 三处，规则为默认 `unresolved`。不得盲改其他模块。详细位置与表达式见 design 同名补充签认段及 verification 的门禁待登记项。
- 确认意见：授权确认上述登记，用于关闭本轮回滚修复的两项门禁。不包括全量验收或其他未列明范围。若出现额外未知差异，不得捎带登记，须另行报批。
