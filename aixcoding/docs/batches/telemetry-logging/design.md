# 设计：企业埋点上报日志

- 责任人：兰荣达
- 状态：已确认
- 确认日期：2026-11-13
- 确认意见： 已确认

## 方案概述

对应 [ADR-telemetry-logging--report-detail](../../standards/adr/telemetry-logging--report-detail.md)。默认关闭，通过进程环境 `AIXCODING_TELEMETRY_LOG_PAYLOAD=1` 启用。独立上报发送层在实际 POST 处生成一条结构化记录，复用同一次发送的 JSON 对象。发送结果补齐 HTTP 状态或异常类型和单调时钟耗时，随后经 detail logger 记入 `aixcoding-logs/aixcoding.detail.log`。载荷以无截断 JSON 字段写入，保留字段值和结构，日志不读取认证头。记录自带本地序号供界面选择，报文存在 `requestId` 时展示原值。

F6 → `aixcoding` 页签新增专用详情入口。定制组件通过会话内有界缓冲读取同一条结构化记录，列表展示接口与结果，选中后用可滚动的只读纯文本组件展示和复制完整 JSON。按总字节和条数控制保留量，淘汰最旧整条记录，单条大记录仍能查看完整内容。缓冲独立于面板生命周期，打开面板前产生的记录也可查看。生产者不操作 UI，展示文本按普通文本处理。文件日志与 TUI 分别使用现有轮转和独立内存缓冲，排查历史以文件留存为准。

## 备选方案对比

| 方案 | 收益与代价 | 上游接触面 | 结论 |
|---|---|---|---|
| 独立结构化记录，F6 挂专用组件 | 完整参数可查看和复制，保留日志分层 | 一个 TUI 文件，两处薄接线 | 建议采用 |
| detail logger 冒泡到普通 F6 | 接线少，但 root sinks 也会接触 detail；普通行会截断 | 可能扩散到日志限额和复制逻辑 | 否决 |
| 只写文件 | 零上游接触，但无法在 F6 看明细 | 0 | 仅在责任人收窄需求时可选 |

## 上游改动清单（R2）

| 文件 | 改什么 | 预估行数 | 标记位置与归属 |
|---|---|---|---|
| `src/chrys/app/tui/screens/logs/screen.py` | 导入定制组件；在 `LogViewerScreen.compose` 的 `aixcoding` 页签内挂载 | +3～6 / −0，含标记 | 导入区与 `compose` 各一处标记。导入和宿主插槽必须在宿主连接；启用判断、列表、详情、复制及数据处理均归定制包 |

## 对上游隐式行为的假设

- HTTPX 固定依赖返回的响应扩展可能包含 `network_stream`。已核对本地 httpcore 的网络后端提供 `get_extra_info("server_addr")`。扩展缺失、失败前未获得响应或连接信息无法读取时，显示对端未知，保留实际请求 URL，不使用 DNS 结果冒充连接地址。
- 日志对话框在 `compose` 中生成模块页签。定制组件随 `aixcoding` 页签挂载，沿用宿主的生命周期和布局。若上游重写页签布局，行为锚定测试需发现入口丢失。

## 文件与改动清单

| 文件 | 用途 |
|---|---|
| `src/chrys/service/aixcoding/telemetry/delivery.py` | 在现有 POST 周围采集，复用报文与状态 |
| `src/chrys/kernel/aixcoding/diagnostics/telemetry_reports.py` | 结构化记录、显式开关、detail logger 和有界缓冲 |
| `src/chrys/app/aixcoding/tui/telemetry_logs.py` | 展示并复制完整详情 |
| `src/chrys/app/tui/screens/logs/screen.py` | R2 薄挂点 |
| `aixcoding/tests/telemetry/test_report_logging.py` | 行为锚定、日志与请求对拍、边界测试 |
| `aixcoding/docs/standards/DEVELOPMENT.md` | §9 日志分层条款补一处专用入口边界，普通主卷及通用日志流仍遵循现行规则 |
| `aixcoding/manual/{en,zh-Hans}/reference/settings.md` | 使用说明：开关、F6 入口、文件位置 |

## 定制点登记预告

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| telemetry-logging:detail-pane-import | src/chrys/app/tui/screens/logs/screen.py | AIxCoding Telemetry log detail pane import | 1 | LogViewerScreen.compose | 低 | 上游有可注册的 F6 模块内容插槽 |
| telemetry-logging:detail-pane-slot | src/chrys/app/tui/screens/logs/screen.py | AIxCoding Telemetry log detail pane slot | 1 | LogViewerScreen.compose | 中 | 上游有可注册的 F6 模块内容插槽 |

## 风险与回滚

原样载荷可能包含代码片段或工具输入，因此以显式开关控制采集。文件轮转可能淘汰历史记录，日志系统或连接信息读取失败时上报继续。关闭开关可停止采集；回滚本批改动可撤除入口。

## ADR 判定

四问依次为是、否、是、是。否决普通日志冒泡方案；局部实现可回退；专用明细入口改变跨批次展示规则；依赖上游 F6 页签构造和 HTTP 传输扩展。新 ADR 仅调整专用入口的适用范围。
