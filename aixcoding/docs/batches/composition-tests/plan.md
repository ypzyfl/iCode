# 任务清单：服务组合测试（composition-tests）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

双 AI 自审完成（2026-11-01，Kimi-K3.1-Pro 评审：一轮收敛，blocker 0 / suggestion 0 /
nit 0，独立复跑通过；self-review.md 草案已生成）。下一步：责任人签认 self-review.md →
组装 PR 描述 → git 提交（逐条授权）。

## 待办

- [x] 责任人审阅并签认 design.md（R10：2026-11-01 周彬签认）；
- [x] 起草 test-plan.md（覆盖矩阵：验收标准逐条 × 用例；钉死 stack 调用形态——`get_response`
      消息构造、调用形态硬约束五条（design 决策三）与快照计数基线；登录态建立禁令、
      同一性断言（`_default_session` patch）、资源生命周期、auto 模式时序基线逐条落验收；
      行为锚定清单对照 design 假设 1-5）；
- [x] 实施 `aixcoding/tests/auth/test_composition_lifecycle.py`（测试 + `_LoopbackLLM` stub
      同文件；环境前置/同一性断言/三次快照断言按 design 实施硬约束；主用例一次通过）；
- [x] 验证：`uv run python aixcoding/tools/verify.py --smart`（本地双通道）+ ruff
      （aixcoding/tests 目录级豁免已就位）；证据落 verification.md（V1）；
- [x] 双 AI 自审（SELF-REVIEW-HOWTO：换一个不同 AI 评审 → 修复 → 复审循环），产出
      self-review.md（2026-11-01 Kimi-K3.1-Pro：一轮收敛零 finding，独立复跑 1 passed
      2.45s；待责任人签认）；
- [ ] 组装 PR 描述（§7 结构），特性分支提 PR，双 CI 门绿后合并（PR 流程规范）。

## 挂起与备忘

- **stub 提取义务**：`_LoopbackLLM` 现为测试文件内单消费方实现（design 决策二）；将来出现
  第二消费方（如 telemetry 契约、TUI pilot）时再评估提取位置（tests/ 内共享 helper 或
  `aixcoding/mock/llm/` 专区子包 + 契约测试义务），不在本批做；
- **已知边界（预案钉死不塞本批）**：TUI 全屏交互/真实 UI 生命周期验证缺口显式登记于
  requirements 非目标，后续独立决策；模型目录缓存、diagnostics 面板同；
- 预算监控口径（P0 批次）：Windows 开发机定制套件中位数 >1min 或 P95 >2min 时评估分区；
- 本机环境噪音在案：mock 7777/7778 端口被占用类问题（auth-isolation-mock-ports 批次后
  launcher 已动态端口化，组合测试进程内 `port=0` 不受影响）。
