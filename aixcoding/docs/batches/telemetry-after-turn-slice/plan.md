# 批次1 plan：telemetry-after-turn-slice

> 活文档。上游：探索批次（`feat/telemetry-exploration` 长期根分支）；分支：`feat/telemetry-after-turn-slice`（工作块分支，PR 回长期分支触发双 CI）。

## 当前状态（2026-11-20）

- [x] requirements 确认（2026-11-20）
- [x] mock design 单端口修订 + DIRECTORY 调整（统一端口 15678，签认含三轮 review 修复）
- [x] design.md 签认（=R2 批准 §2 七文件 + D1 §5 清单；2026-11-20）
- [x] CI 触发前提（长期分支 commit `a9e79024`）
- [x] V1–V3 判别实验（5 passed，结论见 verification.md：reader 按 exchange 归属过滤、A-final 须 trajectory 补全、dispatcher 三元组键）
- [x] 上游 R2-1~4 + 定制 notice/dispatcher/owner + 单测（2026-11-21：上游回归 1401 passed 零失败；marker 对账 161/0 warning；首轮 import 隔离缺陷发现并修复）
- [x] mock 1A 单端口组合改造 + 契约测试回归（2026-11-21：combined.py 组合层 + launcher 单端口 15678 + 测试 87 passed；独立 factory 未动）
- [x] mock 1B telemetry 存储（2026-11-21 前半：三 save 端点 + join + 原模型捕获钩子 + 组合挂载，契约测试 94 passed）
- [x] reader/analyzer/过滤/reporter×3/client + owner 接线（2026-11-21 后半：端到端 43 passed——真实轮→通知→管线→mock join 闭环；ai-code blocks 为引用形态待批次3 前复核）
- [x] 产品端配置 R2-5~7（local 默认 15678）+ 全 mock 真流量端到端切片（2026-11-23：真流量 join 闭环通过——modelRecord/llmReport/A-final 同原值；定制层文件免 marker 核正；886 passed）
- [ ] 边界矩阵（无 hooks/save=False/trajectory disabled/A1≠A2/flush）→ test-plan 全量 → self-review 签认 → PR 回长期分支（双 CI）
- [ ] 产品端配置 R2-5~7（local 默认 15678）+ 端到端垂直切片
- [ ] 边界矩阵（无 hooks/save=False/trajectory disabled/A1≠A2/flush）
- [ ] test-plan.md 全量 + self-review.md 签认 + PR 回长期分支（双 CI）

## 明确不做（requirements §3 引用）

批次2 ACP/桌面、批次3 parity 矩阵、真实后台联调、上游化、崩溃补报、流式通知。
