# 自评审记录：排队进度提示（model-queue-progress）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：李海潮
- 确认日期：2026-11-18
- 确认意见：（可选）
- 评审 AI：CodeBuddy 子代理（独立会话，只读评审；与开发会话上下文隔离）
- 开发 AI：CodeBuddy（本会话）

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-11-18 评审结论：通过（blocker 已清零）

- 轮次：设计评审 1 轮（落盘 `aixcoding/docs/pr/model-queue-progress设计评审.md`）+ 实现评审 1 轮 + 修复 + 复审
- 评审范围：commit `0b496751` 与工作区修复；R2 最终 16 文件约 126 行
- blocker 处置：
  1. **同轮内文案不释放**（`event_handlers.py` / `view_adapter.py`）→ 已修。根因是放行后没有任何信号，等待行在后续每次等待都会带"排队中"。修法：guard 在首个数据块时上报 `RELEASED_POSITION = -1`，TUI 清文案、CLI 重置去重、ACP 发 `released: true` 并清该会话记录。
  2. **ACP 去重跨会话串号**（`server.py`）→ 已修。判重键改为 `session_id → position` 的字典；放行时删该会话条目；`ext_notification` 成功后才记录（发送失败可重试）。
- suggestion / nit 处置：
  - `query_one(WaitingRow)` 在 chrome 重建窗口可能 `NoMatches` → 改为 `_waiting_row()` 遍历查询，缺失即跳过。
  - `queue_progress.py` docstring 声称 ACP 也 import 本模块 → 已改为"ACP 只透传位置，客户端自绘文案"。
  - CLI 去重不按轮重置 → `TurnProgress.handle` 新增 `TurnStarted` 分支清零。
  - TUI 放行事件缺 `_predates_active_run` → 已补（`_predates_active_run` 的参数 union 同步纳入 `GatewayQueueStatus`）。
  - `verification.md` 记录的"仅当回调非空才传参"与代码漂移 → 已在验证记录中标注为已回退。
- 未修项（责任人拍板不修）：
  - ACP payload 增 `note` 字段由服务端渲染中文（评审 F5 建议）——当前由客户端渲染，与"插件自绘"的既有约定一致，留待联调确认。
  - `WaitingRow` 窄终端裁掉长队列档的可操作建议（F8）——design 假设 3 已接受该副作用。
  - `observer.py` 用 `Any` 承载回调参数（F11）——加 `Protocol` 会引入 service→定制包的类型依赖，收益不抵成本。
- 复审证据：`verification.md` 的「2026-11-18 实现评审修复」节（含三平台 ty、TUI/CLI/ACP 回归与定制测试 19 条）。
- 声明：本评审为独立第二 AI 评审（子代理独立会话），与开发会话上下文隔离；同一模型族仍可能共盲，终裁在责任人。
