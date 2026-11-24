# 原仓新增埋点二进制 CD

- 决定（2026-11-23，按用户明确指令）：在 iCode 原仓基于当前 `cd.yml` 新增 `aixcoding-telemetry-cd.yml`，保留原 CI、六平台矩阵、PyApp 运行时别名、离线依赖和资源包格式；原 CD 不变，首轮仅交付 Actions 验收制品。
- 分工：独立私有埋点仓库交付 wheel 和归档准备工具；新 iCode CD 自动构建固定提交的 wheel、装入内置 Python，再由原编译步骤产出二进制；用户无需手动构建或搬运 wheel。
- 接线：仅新增 workflow，并在 `_common.py::CUSTOM_EXACT_PATHS` 精确登记。复用既有定制 workflow 先例，无宿主业务源码、依赖或 lock 改动；本记录不代替运行时替代方案的完整验收。
- 前置：在 iCode Actions 配置 `TELEMETRY_ADAPTER_READ_TOKEN`，仅授予 `MEDADA/aixcoding-telemetry-adapter` 的 Contents:read；缺少时明确失败，不使用个人 gh 凭据，不静默构建无埋点制品。
- 证据：GitHub 当前基线 `19537fde4d1c47e9bbf5e4f482bcab1973221e51` 的原 CD SHA256 为 `394e5a2804017395ae68272f526200231ff71bba700b63751cbc34ecf7e71b2f`；新文件静态验证保留六平台及关键步骤、Actions 固定 SHA、无生产发布。历史 macOS 内嵌实验与新 wheel-only 流水线成功，不代表本新 CD 已运行或所有平台已验收。
