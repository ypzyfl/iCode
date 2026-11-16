# 需求：后端同步模型与自定义模型共存

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

当前 `apply_catalog()`（`src/chrys/service/aixcoding/models/catalog.py`）在同步成功后
按 `final_names = {后端 id}.yaml` 删除目录里**所有**不在本次后端列表的 `*.yaml` /
`*.yml`（:783-787）。结果是：用户放在 `~/.chrys/models/` 里的自定义模型，只要
后端目录里没有同 id 项，下次同步就被无差别删除。mock README 里「自管模型文件
不会被覆盖删除」的承诺，在 auto_sync 开启后并不成立。

需求是让两者共存：**由后端同步写入的模型要随目录更新（含删除），用户自定义
模型不参与同步、不被删除**。

## 目标与非目标

- 目标：
  1. 后端写盘时给每个模型 YAML 写入标记字段 **`synced_from_server: true`**，
     仅由同步逻辑读写，`ModelProfile` / loader 不感知、不新增 dataclass 字段。
  2. 同步更新时按标记区分：只删除「有标记 且 本次后端不再下发」的模型；
     无标记的自定义模型保留。
  3. ID 冲突（自定义模型 id 与后端某模型 id 相同）：**后端覆盖**，全部同步
     完成后发告警，说明「该 id 的自定义模型被后端同名模型覆盖」。
  4. 告警载体：**仅 detail 日志**（责任人裁决：先不改源码，不做 TUI 主动提示）。
  5. 内存快照保持现有机制（`install_snapshot` 一次原子替换、锁内零磁盘 IO），
     但装入内容扩展为「后端项 + 磁盘上保留的自定义项」，否则自定义模型磁盘在、
     TUI 里看不见。
- 非目标（防止范围蔓延）：
  - **不依赖 `.catalog-state.json` 做标记判定**——该文件继续按现状写入，
    `profile_ids` 语义不变（仍只记后端 id），但同步逻辑不以它区分来源。
  - 不在 `ModelProfile` / `schema.py` / `loader.py` / `app.py` 加字段或解码，
    **零上游改动**。
  - 不改 TUI 只读门禁（保持恒只读，自定义模型继续走文件系统通道）。
  - 不引入「内容未变则跳过写盘」的优化——当前版本每次同步都全量重写，
    指纹只是记录（源码 docstring 明写），本批不改这一行为。
  - 不改后端 payload 契约、不新增配置项、不加第三方依赖。

## 用户场景

1. 用户在 `~/.chrys/models/` 放一个自定义 `my-model.yaml`（无标记），开启同步；
   某次后端下发新模型列表：自定义文件**仍在**，且 TUI 列表里可见、可用。
2. 后端某次下发的模型被移除：下次同步删除对应的 `synced_from_server: true`
   文件；用户自定义文件不受影响。
3. 用户自定义模型 id 与后端某模型 id 相同：本次同步后端覆盖该文件，全部
   完成后 detail 日志出现覆盖原因，TUI 显示一次提示。
4. 升级场景（旧版同步写入的 YAML 无标记）：第一次同步时旧文件被当作自定义，
   若与后端 id 重叠则覆盖 + 告警（一次性迁移告警）；不重叠则保留。

## 验收标准

- [ ] 后端写盘的每个模型 YAML 含 `synced_from_server: true`；解析该 YAML 的
      loader 不因该未知字段报错或把它塞进 `ModelProfile`。
- [ ] 同步删除只针对「有标记且不在本次后端列表」的文件；无标记文件全部保留。
- [ ] 自定义模型（无标记）在同步后仍出现在 `ModelProfileRegistry` 列表里
      （内存快照扩展生效）。
- [ ] ID 冲突：后端覆盖自定义文件；detail 日志记录被覆盖 id 与原因
      （仅日志，不做 TUI 主动提示）。
- [ ] `.catalog-state.json` 内容与写入逻辑不变；同步判定不读取该文件的
      `profile_ids` 作来源区分。
- [ ] 指纹 `_coerce_version` 仍只含后端项、语义不变。
- [ ] 既有 catalog 同步测试不回归；新增契约测试覆盖保留/删除/冲突/告警/快照。
- [ ] 治理门禁：design 签认、六件套齐、`check_docs --closure` 全绿、
      `check_r2_diff` 的 R2 表覆盖所有上游改动、`gen_customizations --strict`、
      ruff / ty / Smart Test 全绿。

## 开放问题

- **TUI 提示挂点（已裁决）**：不做 TUI 主动提示，告警仅进 detail 日志，
  **零上游改动**。Textual 的 `notify()` 是 App/Widget 实例方法、
  `active_app` 是主线程 ContextVar、EventBus 无全局单例，业务层无法直接
  发 toast；为最小化源码改动，本批不引入回调通道、不改 app.py。
- **升级迁移告警**：旧版无标记 YAML 首次同步会产生一次性覆盖告警（场景 4）；
  接受该一次性误报，还是额外做「state 里存在即视为旧后端模型」的迁移兼容？
  后者会重新引入对 `.catalog-state.json` 的依赖，与需求冲突，本批倾向前者。
- 批次目录名 `catalog-custom-coexist`、分支名 `feat/catalog-custom-coexist`
  已由责任人确认（2026-11-16）。
