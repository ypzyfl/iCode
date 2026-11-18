# 任务清单：客户端对接模型并发排队（model-queue-client）

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

首稿经独立评审后已修订（E' 方案 + stall 续活），**待责任人签认**（design.md 头部即 R2 批准记录）。签认后进入 N1 实现。

## 待办

- [x] 需求与方案比选（N1 选定，UI 拆第二批）
- [x] 起草 requirements.md / design.md / test-plan.md / plan.md
- [x] 起草 ADR（`model-queue-client--queue-frame-interception`）
- [x] 按独立评审修订：改 E' 方案（撤销 `_legacy.py` 改动）、补 stall 看门狗续活、补 kernel 档死路论证、测试改走生产入口
- [ ] 责任人签认 design.md 与 ADR
- [ ] 实现定制包 `src/chrys/service/aixcoding/llm_queue/`
- [ ] 一处上游接线（`chat_completions/client.py`）+ AIxCoding 标记（E' 已撤销 `_legacy.py`）
- [x] 定制测试 `aixcoding/tests/llm/`（8 条，含心跳与回退锚定）
- [x] verification.md 记录命令与输出
- [x] self-review.md（独立子代理评审：2 blocker 已修，复审通过）
- [x] 本地提交（7a33a816）+ 自审修复提交
- [ ] 责任人重签 design.md 与 ADR（R2 增列 manifest、行数改 +10/−0）
- [ ] 责任人签认 self-review.md
- [ ] 第二批 UI 批次（另行设计，见挂起）

## 挂起与备忘

- 第二批 UI（排队进度提示）方案未定：新增事件类型需再动 3 个上游文件，须单独立批次设计。
- `QUEUE_FULL` 重试阶梯保持现状（3/7/15…），与网关文档建议的 2/5/10×3 不同，已记录为非目标。
