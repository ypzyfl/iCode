# 计划：llm-call-interception

状态：**惰性化已实施并完成全部回归（安装由策略注册触发，启动组合零改动）；design/ADR 数字更正已确认，惰性化增量评审
通过，3 条 nit 建议已按责任人裁决处置，待提交并由 CI 复验后合并**。惰性化代码上：本批与启动接线 133 passed，完整定制 1010 passed / 56 skipped，真实
startup 50 项组合通过，上游 core shard 37256 passed / 699 skipped，Smart Test 11040/349 + architecture 600/2。原启动
安装任务在真实启动路径上的净增量约 18–20 ms（此前记录的 200 ms 系测量条件缺陷，已更正，见 self-review.md）。
self-review 已由周彬于 2026-11-25 签认。

## 任务清单

- [x] 调研 HTTPX、SDK、Chrys 调用归属、普通/SSE 响应和逻辑层边界
- [x] design.md 责任人签认（周彬，2026-11-25）
- [x] HTTP ADR 责任人签认（周彬，2026-11-25）
- [x] test-plan.md（逐条验收覆盖、真实上游行为锚点、异常与资源路径）
- [x] 实现 `src/chrys/service/aixcoding/llm_call_interception/` 通用框架和默认空策略，独立复审无未关闭发现
- [x] 安装由策略注册触发，启动组合零改动（2026-11-26 惰性化；原“接入 startup”方案经性能评估与更正后由责任人裁决替换）
- [x] 新增 `aixcoding/tests/llm_call_interception/`，conftest 在每个测试前后恢复未包装的工厂
- [x] 验证落盘 verification.md（定制测试、Smart Test、ruff/format、规范校验、零上游手写行为文件及 manifest 例外）
- [x] 双 AI 评审并形成 self-review.md，责任人签认后完成文档闭环
- [ ] 提交：特性分支 + PR（所有 Git 写操作逐条请示授权）→ 已推送、建 PR #153，独立评审与惰性化增量评审均通过；评审处置与惰性化改动待提交，待 CI 复验后合并

## 续接入口

先读本目录 requirements.md / design.md / test-plan.md / research.md，以及
`aixcoding/docs/standards/adr/llm-call-interception--http-startup-runtime-wrapping.md`。
当前不修改任何上游手写行为文件，不新增第三方依赖；唯一例外是官方生成器刷新的架构 wait manifest，该范围
已重新签认并执行。未来逻辑层需求另立设计与 ADR。

性能评估、启动成本测量更正与惰性化裁决见 self-review.md “对原有流程的影响与性能评估”“启动成本测量更正与惰性化重新
评估”两节。后续候选（责任人裁决本 PR 不做）：框架层检测 `HttpChange.headers` 同名多值，详见 self-review.md 未修项表。
