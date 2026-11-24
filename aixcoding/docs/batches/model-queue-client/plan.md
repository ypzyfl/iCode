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

## 变更单 v1.1：排队中主动取消（2026-11-19）

> 契约：`ModelQueueFrontend.md` §3.6、`LlmRequestFlow.md` §5。原非目标撤销，需求与设计见
> requirements.md / design.md 的「2026-11-19」章节。

- [x] requirements 追加（目标 4/5/6、非目标、7 条验收）
- [x] design 追加变更单（方案、假设 6 条、定制点 `queue-cancel`、风险；R2 实际 +28/−9、manifest +14/−1 已回填）
- [x] test-plan 追加覆盖矩阵（10 条 + 降级路径）
- [x] **责任人重签 design.md**（2026-11-19）
- [x] 实现 `src/chrys/service/aixcoding/llm_queue/queue_cancel.py`
- [x] `client.py` 接线（tracker 构造 / `on_status` 包装 / `finally` 取消）
- [x] 定制测试 `aixcoding/tests/llm/test_model_queue_cancel.py`（29 条，`aixcoding/tests/llm` 49 passed）
- [x] mock 网关补 cancel 接口（`mock_server/model_concurrency_verify/mock_gateway.py`，仅本地验证资产）
- [x] verification.md 追加验证节（含 ACP 真实中断实测 + Smart Test 环境性失败的诚实记录）
- [x] self-review 追加一轮（2 轮独立子代理评审 + 3 项破坏实验）

## 变更单 v1.4：上游接线归位压缩（2026-11-24）

> design v1.4 已签认后实施；网关无法感知客户端断连（2026-11-24 责任人裁决），取消链路永久保留。

- [x] client.py 四处接线压缩（导入注释收敛 / tracker 收 sdk / `wire_queue_callback` / `close_stream_and_cancel` 撤销 finally 嵌套改写，保留降级关流分支）
- [x] `queue_cancel.py`：sdk 参数、两个新 helper；`__init__.py` 导出
- [x] `test_model_queue_cancel.py` 改用 sdk 替身；wait 清单刷新（6 条重开均为默认 `unresolved`）
- [x] 实测回填：client.py 相对 base **+30/−1**（v1.4 表）；gen_customizations --strict / ruff / ty 三平台全绿
- [ ] 责任人确认 v1.4 实施回填（净行数高于预估的降级分支说明）

### 阻塞与待确认

- design 重签完成前不进入实现（R10）。
- 联调前需用真实 profile 核对 `base_url` 形态能否推导出 cancel 地址（design 假设 3，最大外部依赖）。
