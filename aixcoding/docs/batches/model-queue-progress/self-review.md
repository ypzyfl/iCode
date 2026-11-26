# 自评审记录：排队进度提示（model-queue-progress）

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
校验：uv run python aixcoding/tools/check_docs.py
-->

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-18
- 确认意见：（可选）
- 评审 AI：CodeBuddy 子代理（独立会话，只读评审；与开发会话上下文隔离）
- 开发 AI：CodeBuddy（本会话）

> 记录档：签认一次，后续追加评审记录不触发重签。

## 2026-11-18 评审结论：通过（blocker 已清零）

- 轮次：设计评审 1 轮（落盘 `aixcoding/docs/pr/model-queue-progress设计评审.md`）+ 实现评审 1 轮 + 修复 + 复审
- 评审范围：commit `0b496751` 与工作区修复；R2 最终 16 文件约 126 行
- R2 回填（2026-11-20，独立评审 C1/C7）：**17 文件、实测约 +191/−7**；`tests/architecture/trajectory_wait_manifest.json` 已补入 design R2 表，正文变更待责任人重签。
- 轮次边界锚定（2026-11-20，独立评审 C0）：新增 5 条（CLI `TurnStarted`、ACP 跨会话去重/released、TUI handler→presenter、presenter→view、view adapter→WaitingRow）。
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

## 2026-11-26 补轮（PR #154 独立评审处置）：覆盖 v1.2–v1.9 断档 + 本日修复

- 缘起：PR #154 独立评审 B1 指出本文件最后记录停在 2026-11-20，其后 v1.2（队首文案）→ v1.3
  （归位改造：事件类迁包、construction 工厂化、ACP/CLI 体入包，修 PR #151 缺陷 1）→ v1.4
  （requestId 透传 + frontend-api.md 契约）→ v1.5（方法名去命名空间 + released 帧）→ v1.6
  （第三帧拒绝）→ v1.7（status 三态）→ v1.8（重试可见性修复 + 取消排队按钮）→ v1.9（评审
  修复批）共 8 个变更单无自审记录。本节补档。
- 断档期的第二评审来源如实声明：v1.2–v1.7 无独立 AI 评审（各单有责任人裁决与验证记录）；
  **PR #154 独立评审（2026-11-26）是这段的第一份独立复核**（上游接触面逐行、门禁复跑、
  84 passed 复验），其对本批 blocker 的裁定：放行文案释放、ACP 去重串号两项"已修"属实。
- 本日新增（v1.9，纯文档/落位；代码面在 client 批 v1.6）：R2 顶层表回填 v1.8 三文件（含更正
  v1.8"测试新文件非上游改动"的错误表述）、frontend-api.md QUEUE_FULL 延期口径、construction.py
  无关折叠恢复、`model_concurrency_queue/` 迁入本批目录、`pr/` 评审记录退未跟踪、活文档清扫、
  v1.7 补 ADR 判定节。无 marker/登记表变化。
- v1.8（重试可见性 + 按钮）与 v1.9 的**门禁与测试从未在任何环境跑过**（本机无 uv）：以推送后
  CI 为准，结果回填 verification.md；推送后另有 AI 复评轮，发现将追记本节。
- 声明：本节为开发 AI 补档 + 外部评审引用，非独立子代理评审；终裁在责任人。

## 2026-11-26 AI 复评轮（推送前本地，PR #154 步骤 4）

- 范围：v1.8 全部代码面（queue_cancel_button.py / waiting_row.py / panel.py / screen.py / 两个新测试
  文件）+ v1.9/v1.6 文档批 + M1 代码面。
- **发现并修复 2 个 strict 门禁红点**（均在 v1.8 登记行，从未过 CI）：
  1. `waiting-row` 行把 marker 锚写成 `A / B` 多选并档计数 3——`gen_customizations` 的锚匹配是
     **逐字前缀**（`startswith`），无多选语法 → orphan + 新 marker 无登记双重失败。拆为
     `waiting-row`（锚 `waiting row note`，1）+ 新登记点 `waiting-row-cancel`（锚
     `waiting row cancel button`，2）。
  2. 三个 v1.8 新行的 `预期计数` 带中文括注（如 `2（v1.8 新增点：…）`）——计数字段是**严格整数
     解析**，非整数行被忽略同样触发无登记 error。计数改纯数字，括注挪入 anchor 列。
- 复刻验证（本机 3.13 等效实现扫描与最长锚优先匹配）：三个触碰文件的登记行全部命中且无
  未吸收 marker；全仓非整数计数清零；R2 池复刻 unauthorized 清零（v1.8 三文件入池）。
- 其余核点无发现：行宽全 ≤120（两处 >120 为上游存量 docstring/noqa）；ClickAffordance
  构造/CLICK_MESSAGE 协议、`add_retry`/`add_user_message` 签名、`notify(markup=False)` 先例、
  import 序（aixcoding < tui）、`on` 已导入、`_chrome.waiting_row` 存在。
- 局限：本机无 uv，py_compile 与复刻之外的全部验证仍以 CI 为准（chat_completions/client.py 为
  PEP 758 语法本机不可编译）。
