# OTel 企业业务埋点二进制 CD

- 决定（2026-11-23，按用户明确指令）：在 iCode 原仓基于当前 `cd.yml` 新增 `aixcoding-otel-business-telemetry-cd.yml`，保留原 CI、六平台矩阵、PyApp 运行时别名、离线依赖和资源包格式；原 CD 不变，首轮仅交付 Actions 验收制品。
- 方案领域：LLM / Agent 企业业务埋点，涵盖模型调用关联、工具执行、代码生成、审批及桌面 Agent 使用。保留宿主原生 OTel；独立 Python 业务适配器通过运行时包装、中间件和 EventBus 事件订阅采集，模型请求携带企业 telemetry 扩展，工具与代码等报文直接按企业 HTTP 协议发送，不依赖 session 重建或 OpenLLMetry。
- 分工：独立私有埋点仓库交付 wheel 和归档准备工具；新 iCode CD 自动构建固定提交的 wheel、装入内置 Python，再由原编译步骤产出二进制；用户无需手动构建或搬运 wheel。
- 接线：仅新增 workflow，并在 `_common.py::CUSTOM_EXACT_PATHS` 精确登记。复用既有定制 workflow 先例，无宿主业务源码、依赖或 lock 改动；本记录不代替运行时替代方案的完整验收。
- 前置：在 iCode Actions 配置 `TELEMETRY_ADAPTER_READ_TOKEN`，仅授予 `MEDADA/aixcoding-telemetry-adapter` 的 Contents:read；缺少时明确失败，不使用个人 gh 凭据，不静默构建无埋点制品。
- 证据：GitHub 当前基线 `19537fde4d1c47e9bbf5e4f482bcab1973221e51` 的原 CD SHA256 为 `394e5a2804017395ae68272f526200231ff71bba700b63751cbc34ecf7e71b2f`；新文件静态验证保留六平台及关键步骤、Actions 固定 SHA、无生产发布。历史 macOS 内嵌实验与新 wheel-only 流水线成功，不代表本新 CD 已运行或所有平台已验收。

## 2026-11-24 资源包与验收记录修正

- 按用户确认的修复范围，每个平台在原生 runner 上压缩二进制，解压同一资源包后运行完整业务 smoke。汇总 job 收集已验证的归档，避免裸二进制经 Actions artifact 传输丢失执行权限后再打包。
- 默认适配器更新至 `ebe9895ff8573d9ef74b8923ef511cbbf33e60e7`，纳入完整 ACP 允许/拒绝 smoke。每个平台的资源包旁保留构建 manifest 与 smoke 摘要，记录宿主 SHA、适配器来源、运行时事实及二进制/归档摘要。失败时上传已有 JSON 验证记录。
- 回归测试直接执行 workflow 内的打包代码，覆盖 Linux/macOS tar 与 Windows ZIP 布局，模拟 artifact 将外层文件权限归一为 0644，检查解压后二进制内容、Unix 执行权限和构建来源。
- 本次仍使用固定源码 SHA 构建伴随包。本仓 Release 契约落地后再接入版本化下载；六平台运行与真实业务验收以 Actions 实际执行结果为准。
- 本地验证（Python 3.14.8，复用现有宿主测试依赖）：资源包回归 3 passed；Smart Test 选择的架构检查 200 passed（沙箱阻止进程优先级调整的两项在沙箱外重跑通过）；Ruff、22 个 shell 步骤语法、嵌入 Python、文档闭环与定制登记检查通过。尚未运行六平台真实编译及制品 ACP smoke。
