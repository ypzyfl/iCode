# 测试方案：企业埋点迁移

旧版使用隔离配置、工作区和本地记录端点，录制真实 wire JSON。新版回放同一输入、审批与模型响应，比较 `body.telemetry`、`tool-detail`、`ai-code` 及 ACP 元数据。两边记录独立发送顺序和关联。ID 归一化保持等值关系，不抹去缺失或错挂。

以下为拟新增测试入口，均落在 `aixcoding/tests/telemetry/`。行为锚定用真实上游组件，mock 只替换模型和远端上报服务。

| 需求 | 拟定入口 | 断言与场景 |
| --- | --- | --- |
| T01 | `test_model_wire.py` | 经 `_assemble_stack` 的真实模型客户端，对拍三种协议、流式、辅助调用、SDK retry、wire retry、stall fallback、blank/overflow 和 thinking-binding resend。服务端存储单列 POST 重建与 GET 续读，检查工具归属、额外请求字段及旧报文 ID 的等值关系。 |
| T02 | `test_tool_reports.py` | 实际工具中间件发布 Start/Result，覆盖成功、审批拒绝、审批改参、超时、失败和取消。断言 save/PENDING/终态顺序和旧缺省。 |
| T03 | `test_code_reports.py` | 真实写入和快照 A→B→A、CRLF、replace_all、空文件、纯删除、大文件。比较每次行数、片段范围和 `codeStatus`。 |
| T04 | `test_usage_reports.py`、`test_acp_metadata.py` | 引擎真实解析普通和追加输入，加载技能双维度，ACP 正常/取消及选择 Agent 无模型请求。检查旧与新 envelope 共存。 |
| T05 | `test_common_fields.py` | 旧环境优先级、凭据变化、工作区与启动目录不同、Git detached HEAD、Windows 路径、渠道。 |
| T06 | `test_correlation.py` | 主 Agent 先后调用及并发子 Agent 复用 provider ID。断言 exchange、工具 operation 和逐次快照一一对应，重试后只关联实际执行的调用，历史 restore/fork/replay 不计新事件。 |
| T07 | `test_delivery.py` | 首事件注册、恢复、重复注册、禁用、服务器延迟/拒绝、队列满和关闭。断言上报故障不改变业务结果。 |
| T08 | `verification.md` 的跨版本演练记录 | 保持编码器和 fixture，换上游基线后跑全部契约，记录接线变更与残留差异。 |

T02 / T06 检查 Start 和 Result 的操作身份一致，包括审批改参和 metadata 重绑。Workflow 节点在工具已完成后超时并恢复时，第二次 attempt 不产生重复工具上报。分别验证有轨迹上下文和无轨迹上下文。

托管工具覆盖主轮、子 Agent 和 Workflow。验证流式 Start 在最终响应之前发布，成功时关联实际模型调用，首次在 GET 续读观察到的工具使用该次续读 ID，POST 已发布 Start 时 GET 只完成已有记录。模拟失败、同会话并发、重复 provider ID 和事件迟到，断言三个关联字段只取实际来源，无法确认来源时缺省。核对旧版样本中的记录数、顺序和状态，并将纠正的关联差异单独断言。

先做 T01 的最小记录探针和 T02/T03 的真实事件探针。观察同一逻辑调用的 HTTP 次数、最终参数读取位置、稳定 ID 与快照能否到达适配器。缺字段时输出源头和受影响用例，更新 R2，再定正式接线。旧版无法产生的新版专属场景做不变量测试，不能记作新旧对拍通过。

R2 额外验证工厂构建上下文的作用域。三条构建路径沿用原工厂实参，工厂失败或取消时保持原错误和关闭语义，两个并行构建使用各自的 profile 与 workspace。验证每条路径的首个模型请求及首个工具事件，并确认开关关闭和接线导入失败时引擎继续运行。

R2 实施验证使用仓库统一入口 `uv run python aixcoding/tools/verify.py --smart --paths <本批次改动路径>`，另执行 Ruff、格式检查、目标平台 ty 检查及定制登记严格对账。按逐行审阅稿刷新 wait manifest 并复核重新打开的等待。升级演练和全字段报文对拍见 T08 和设计 §8。
