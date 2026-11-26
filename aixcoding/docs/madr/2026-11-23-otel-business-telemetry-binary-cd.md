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

- 2026-11-24 Windows CI 修正：测试显式选择 Git Bash；摘要解析同时识别 sha256sum 的 text 空格标记与 binary 星号标记。三种资源包布局分别执行原生默认模式与显式 binary 模式，避免 Windows text 模式转换归档字节。在 Unix 本地先复现 binary 模式三项失败，修正后六项通过；保留每个文件的内容摘要校验。

## 2026-11-24 消费伴随包 Release

- 伴随包已发布 `v0.1.0a4`，来源提交 `09a392a7c790339186536d760cd627bc0c42edb4`，manifest SHA256 为 `8cd05caedd54506e64ffbde17d3aeb8fe967cbf1605f46a88f68b51c0a08a92d`。该版本的固定宿主环境安装验证与 59 项单测通过。
- CD 改为消费 `adapter_release` 与 `adapter_manifest_sha256`，先核验固定 manifest，再下载 wheel、工具及验证报告，逐项检查摘要和工具归档布局，保留同一 manifest 作为最终制品的适配器来源记录。
- 私有 Release 下载仍通过上游专用只读 secret，原生编译、六平台矩阵和最终资源包验收继续由 iCode 执行。

## 2026-11-24 Windows 隔离目录修复交付

- 默认伴随包更新为已发布的 `v0.1.0a5`，来源提交 `cc6ac417a558ca8d81fae2fa033b2a6c0b48c827`，正式 `release-manifest.json` SHA256 为 `7fb24304c7d873fac1de712b208a7743a9121d3e11307caaa95b66f771a05633`。版本和摘要必须成对消费。
- 修复来自伴随包 PR #3：在首次启动 PyApp 前创建隔离用户的 AppData/XDG 目录，解决 Windows 首次 `--version` 的 `unable to find platform directories`。未改宿主运行时代码或依赖。
- 正式发布工作流 https://github.com/MEDADA/aixcoding-telemetry-adapter/actions/runs/45378593083 成功；Windows x64、ARM64 原生目录 API 检查通过，固定宿主环境安装 wheel 后 61 项单测成功（Linux 跳过 1 项 Windows API 检查）。已下载全部正式资产，使用伴随包校验器和本仓输入校验器核验摘要、来源、报告及工具布局。
- 本次仅更新输入组合；完整平台资源包与业务/ACP smoke 以新 CD 运行结果为准。历史 a4 不覆盖，回滚必须恢复整套已验收组合。

## 2026-11-24 Windows capture 原生权限修复 a6

- 正式输入更新为 `v0.1.0a6`，来源 `5bad49e6387b2587bcc3f5a61446d5881f4992d7`，manifest SHA256 `85f70b89837e88a42f8c0394368107c623f2b64ae9ddda993f44c95abed73f5a`。[发布工作流](https://github.com/MEDADA/aixcoding-telemetry-adapter/actions/runs/45389339554) 全部成功；五项正式资产经下载及两侧校验器核验。
- a5 已通过实际 Windows 冷/热启动和管理命令，随后 ACP capture 缺失；原生回归在 x64、ARM64 复现 `os.O_NONBLOCK` 不存在。a6 Windows capture 改用宿主既有 `secure_open_owner_only_append`，验证真实 owner-only DACL、普通文件及无重解析点，保留二进制追加语义；POSIX 路径不变。未修改宿主源码或增加运行时依赖。
- Windows x64、ARM64 各 9 项目录/协议测试及 2 项 capture/ACL 回归通过；固定宿主安装 a6 wheel 后 63 项单测成功（Linux 跳过 3 项 Windows 检查）。独立审查未发现问题。
- 上一轮 CD 45379196497 的宿主完整 CI 在定向重跑两项 TUI 时序失败后成功，Linux x64、ARM64 和 macOS x64 实际制品通过；Windows x64 的 a5 capture 未通过，未记为完整平台验收。其余旧版本构建已停止，以新一轮完整 CD 结果为准。


## 2026-11-26 跨天重跑的输入保留期

- a6 CD 45390134429 第三次运行已通过完整宿主 CI，但六平台在下载 `telemetry-wheel` 时全部失败。该中间输入原仅保留 1 天，初次上传后跨天排队/重跑时已不可用；新构建的宿主 wheel 可下载，缺失的是早先成功作业的适配器输入。
- 将已校验的 `telemetry-wheel` 保留期改为 14 天，与最终验收资源包一致，避免仅重跑失败作业时复用已过期的成功输入。固定 Release、manifest 校验、只读凭据和所有 CI/smoke 门禁保持不变。
- 本次从头发起新的固定源码/固定 a6 输入构建，不将保留期修复视为二进制验收通过。仍需六个平台的实际制品 smoke 和最终收集全部成功。

