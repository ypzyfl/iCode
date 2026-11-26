# 计划：llm-call-interception

状态：**实现、评审、最终强制回归和文档闭环均完成；PR #153 独立评审通过，评审处置改动待提交；性能评估发现启动期
回退，惰性化是否实施待责任人裁决**。空策略不附 hooks，真实 startup 50 项组合通过，上游 core shard 37256 passed /
699 skipped；完整定制套件 1008 passed / 56 skipped；实际内容 sniff、误标、缓冲 SSE、增量与关闭契约均通过。
self-review 已由周彬于 2026-11-25 签认，closure 通过。

## 任务清单

- [x] 调研 HTTPX、SDK、Chrys 调用归属、普通/SSE 响应和逻辑层边界
- [x] design.md 责任人签认（周彬，2026-11-25）
- [x] HTTP ADR 责任人签认（周彬，2026-11-25）
- [x] test-plan.md（逐条验收覆盖、真实上游行为锚点、异常与资源路径）
- [x] 实现 `src/chrys/service/aixcoding/llm_call_interception/` 通用框架和默认空策略，独立复审无未关闭发现
- [x] 接入 AIxCoding 自有 startup，保持安装失败独立 containment
- [x] 新增 `aixcoding/tests/llm_call_interception/` 并更新 startup 精确清单测试
- [x] 验证落盘 verification.md（定制测试、Smart Test、ruff/format、规范校验、零上游手写行为文件及 manifest 例外）
- [x] 双 AI 评审并形成 self-review.md，责任人签认后完成文档闭环
- [ ] 提交：特性分支 + PR（所有 Git 写操作逐条请示授权）→ 已推送、建 PR #153，独立评审通过；评审处置与性能评估记录待提交，合并方式待裁决

## 续接入口

先读本目录 requirements.md / design.md / test-plan.md / research.md，以及
`aixcoding/docs/standards/adr/llm-call-interception--http-startup-runtime-wrapping.md`。
当前不修改任何上游手写行为文件，不新增第三方依赖；唯一例外是官方生成器刷新的架构 wait manifest，该范围
已重新签认并执行。未来逻辑层需求另立设计与 ADR。

性能评估结论与待裁决项见 self-review.md “对原有流程的影响与性能评估”一节。后续候选（责任人裁决本 PR 不做）：
框架层检测 `HttpChange.headers` 同名多值，详见 self-review.md 未修项表。
