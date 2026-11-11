# 需求：模型目录 auto_sync 开关（LOCAL 默认不自动同步）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

LOCAL 环境为外网开发准备，配套 mock server（`aixcoding/mock/`）。mock catalog 下发的模型
`apiBase` 指向 mock 自身（`http://127.0.0.1:7777/v1`），其 `/v1/chat/completions` 只回固定文本
（"Acknowledged by the chrys model-catalog mock LLM."），**目录里的模型无法实际使用**；外网开发人员
也无法获得团队共享的真实大模型端点。

现状 LOCAL 下三个自动同步触发点——启动 `sync_catalog_blocking()`（`app.py:1510`）、登录后
`resume_sync_runtime()`（`login_actions.py:163`，`immediate` 默认 True）、15 分钟轮询——任一成功即**整体替换**
`~/.chrys/models/`：mock 假模型覆盖并删除用户自配的模型文件。被覆盖后 LOCAL 用户没有任何可用模型。

目标：LOCAL 默认不自动同步，模型目录归用户自管（手放指向真实 OpenAI 兼容端点的 yaml 即可使用）；
同时保留经 mock 同步的测试能力（显式配置恢复自动同步，现有六模式验证路径不变）。

## 目标与非目标

- 目标：
  1. `[model_catalog] auto_sync` 三态键：未设置按 tier 默认（**local 关、dev/prod 开**）；
     显式 `true`/`false` 全 tier 覆盖默认。
  2. auto_sync 关时三个自动触发点全部不执行（启动 / 登录后 / 轮询）。
  3. auto_sync 关且从未同步成功（无 `.catalog-state.json`）时目录归用户
     （`is_catalog_managed()` 返回 False）；state 已存在时维持 sticky server-owned 语义。
  4. DEV/PROD 未设置时行为与现状完全一致（零行为漂移）。
  5. **零上游文件改动**：全部改动落 fork 定制层，复用既有接线（C034 等）。
- 非目标：
  - 手动同步 CLI/TUI 命令（后续候选批次；本批次测试者经 TOML `auto_sync = true` 恢复）。
  - TUI 模型管理 UI 解禁：F4 入口 / `ModelConfigScreen` 仍全局只读禁用
    （`read_only=True` 硬编码于 `config_actions.py:286`，不消费 `is_catalog_managed()`；
    C035/C036/C038 不动）。LOCAL 用户自管模型的通道是文件系统。
  - mock LLM 真实推理 / 上游透传（独立议题，见开放问题）。
  - auto_sync 环境变量覆盖（本批次仅 TOML 键）。
  - sticky state 一键 reset 命令（以文档说明手工删除 state + yaml 的恢复操作代替）。

## 用户场景

1. **外网开发人员（主场景）**：`AIXCODING_ENVIRONMENT=local` 启动，不配置 auto_sync；往
   `~/.chrys/models/` 放自有模型 yaml（真实端点 + 自有凭证），TUI 正常加载使用；mock 不起、
   不登录均不影响，已有文件不会被覆盖删除。
2. **测试者验证 catalog 同步链路**：`aixcoding.toml` 显式 `[model_catalog] auto_sync = true`，
   起 mock、登录，按现状路径验证 ok/empty/invalid/error/slow/stale 六模式。
3. **DEV/PROD 用户**：无感知，未配置时自动同步行为与现状一致。

## 验收标准

- [ ] 未设置 auto_sync 时：local 下启动与登录均不发起 catalog 请求（无网络调用、目录内容不变）；
      dev/prod 下行为与现状一致。
- [ ] `auto_sync = false`（任意 tier）：三个自动触发点均不执行；无 state 时
      `is_catalog_managed()` 为 False；有 state 时仍为 True（sticky）。
- [ ] `auto_sync = true`（local）：三个自动触发点行为与现状一致，可完成 mock 同步。
- [ ] 非法值（非 bool）：warn 后按未设置处理，启动不崩溃。
- [ ] local 未设置且目录已有用户 yaml：启动、登录、会话全程文件原样保留。
- [ ] `aixcoding/mock/model_catalog/README.md` 含 LOCAL 自管操作说明：默认不同步行为、
      放置自有 yaml 的方法、显式恢复自动同步、恢复自管的显式动作（删 state + yaml）。

## 开放问题

- 手动同步命令（CLI/TUI）：后续候选批次；届时 DEV/PROD"服务端改配置立即拉取"场景一并受益。
- mock LLM 透传真实端点（`--llm-upstream` 代理）：与本批次互补的独立议题——本批次解决
  "目录归谁"，透传解决"mock 模型能否真推理"；暂不立项。
