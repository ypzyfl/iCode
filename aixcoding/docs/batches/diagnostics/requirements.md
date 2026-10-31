# 需求：本地诊断包（aixcoding diagnostics）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载（2026-10-25 已签认，含 R2 批准）。

## 背景与问题

定制层缺自有诊断设施：定制代码问题（遥测缺失、登录异常、降级路径）发生时无可查日志、无崩溃现场、无环境快照，排查依赖复现。上游日志体系面向产品主流程，不适合直接承载定制层观测（受众/时机/过滤策略不同，design 备选对比已论证）。

## 目标与非目标

- 目标（design.md 三组件，全部落 `src/chrys/aixcoding/diagnostics/`）：
  - **定制日志落盘**：`aixcoding.*` logger 子树 + `RotatingFileHandler` 落盘恒开 + `propagate` 开关（F6 面板可选冒泡）；
  - **配置**：`~/.chrys/aixcoding.toml` 解析（tomllib 只读；定位为定制层共享配置基建，后续定制功能扩展此文件）；
  - **崩溃现场**：faulthandler + sys/threading excepthook + atexit 兜底，写会话目录；
  - **环境快照**：启动环境（版本/平台/开关，脱敏）；
  - **launcher**：`python -m chrys.kernel.aixcoding.diagnostics.launcher` 装钩子后调上游入口，零上游文件改动（ADR-0011 回迁后路径）。
- 非目标：
  - 不做遥测上报（旧分支功能，阶段三迁入）；
  - 不做远程/后端对接；
  - 不改上游日志体系（仅 MODULE_ORDER 白名单一行，R2 已批）；
  - 不引入第三方依赖（tomllib/logging 标准库足够，R11 无申请）。

## 用户场景

1. 定制功能异常 → 查 `~/.chrys/` 下 aixcoding 日志文件（落盘恒开，无需事先开启）；
2. 进程崩溃 → 会话目录有 faulthandler 现场快照与环境快照；
3. TUI 中按 F6 → "aixcoding" tab 看实时日志（`tui.panel=true` 时）。

## 验收标准

- [ ] `aixcoding.*` 子树 logger 落盘恒开（`RotatingFileHandler`，默认路径 `~/.chrys/aixcoding-logs/`），与上游日志体系互不干扰；
- [ ] `~/.chrys/aixcoding.toml` 解析：`[logging] level / panel` 等键；文件缺失/非法时安全默认值（fail-safe，日志不中断）；
- [ ] `propagate=true 且 panel=true` 时记录冒泡至上游 `_TuiLogHandler` → F6 显示 aixcoding tab；假设失效时降级为纯落盘无错误；
- [ ] 崩溃（Python 异常 / 段错误级）现场写入会话目录，含环境快照；
- [ ] launcher 以 `python -m` 方式工作：装钩子后调上游入口，正常启动/退出；
- [ ] `screen.py` MODULE_ORDER 一行带 R3 标记落地（R2 已批）；
- [ ] 定制测试全绿（`uv run pytest aixcoding/tests`），含配置解析、logger 行为、崩溃钩子、快照脱敏各层。

## 开放问题

- 无（设计三组件、配置落点、启用方式均已定稿；快照脱敏字段清单在 test-plan 细化）。
