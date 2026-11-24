# 上游 v0.37.0 working-directory 支持对 telemetry 探索的影响评估

> 2026-11-24。性质：探索结论随上游升级漂移的处理（design.md「风险与最坏情况」第 2 条）。活文档，不签认。
> 基线：fork 0.35.2；上游 v0.37.0 = `08175eaa`（2026-11-24）。分析方式：只读核对本地原仓 clone（`D:\Tech\Github\huawei\iCode\iCode`）已有的 v0.37.0 tag，逐文件 diff；未做三方合并模拟，未在 0.37.0 上运行测试。

## 1. 结论（TL;DR）

不构成方向性重大变化。v0.37.0 的 working-directory 支持没有改动「分析 Session 文件」路线依赖的任何数据源或上游接缝；探索方向与三个批次划分保持不变。需要跟进的是升级后的复验（见 §5），不是改设计。

## 2. v0.37.0 相关改动拆解

v0.36.0..v0.37.0 共 33 提交 / 531 文件，与我们相关的是三件事（提交哈希为上游非合并提交）：

### 2.1 `ff156a03`：目录作用域 project → workdir 改名（88 个产品源码文件，+1895/-1213）

「按目录生效」的配置（settings、hooks、skills、快捷命令、workflows、usage、approvals）以前用 project 指代作用目录，现统一改称 working directory：

- 代码参数改名：`load_settings(project_root=)` → `load_settings(workdir=)`；
- 命令参数：审批 `--project` → `--workdir`（`--project` 仍作为别名保留）；
- 审批作用域 `PROJECT` → `WORKDIR`；会话级审批按工作目录分开记录，工作目录级审批可跨会话复用；
- 首次启动迁移 settings/approvals/workflow records 到 workdir 格式，原件备份到 `<config_dir>/backups/<版本>/`；迁移后旧版本读不了这些记录（不可降级）。

### 2.2 `9b28841d`：按 ID 恢复会话，默认用保存的工作目录（25 个文件）

- `-s <ID>` 在 TUI / headless（`run`）/ 浏览器（`serve`）三个入口统一，支持 12 位短 ID 或完整 UUID；
- 打开时默认采用会话保存的工作目录（`session.json` 的 `meta.primary_cwd`）；目录已删会提示；会话被占用报 `session_in_use`；
- 引擎取法 `event.primary_cwd or saved_cwd or self._workspace_cwd()` 与 0.35.2 逐行相同（`session_lifecycle.py` 0.35.2:1513-1516 → 0.37.0:1528-1531，仅行号偏移）。该能力是把引擎既有逻辑开放到启动入口，不是新逻辑。

### 2.3 `5a14262d`：重载会话时重放压缩 turn（12 个文件，同批进入，非 working-directory）

- `session/load`、`session/rollback` 先重放折叠段再放当前历史；`session/history` 结果增加 `compressedBlocks[].messages`；
- 属读取/重放路径变化，非写入路径。

## 3. 逐项核对表

| 影响面 | 核实结果 |
|---|---|
| 会话文件迁移重写 | `migrate_session_envelopes`（`service/state/_session_files.py`）只重写 `meta.kind=="workflow"` 的会话且先备份；普通 chat 会话 `session.json` 不被触碰。workflow 已裁定不在 telemetry 范围 |
| `session.json` 结构与目录布局 | 未变：顶层仍 `meta`+`state`；目录仍 `<sessions_dir>/<短ID>`，与 cwd 无关 |
| trajectory 事件（reader 权威源） | 0.37.0 零改动：`foundation/trajectory`、`service/trajectory`、`service/analytics/turn_trace.py` 均无文件变化；按三个事件常量检索到的 5 个引用文件在 v0.36.0..v0.37.0 均无改动 |
| 批次1 四个上游接缝文件 | `turn_state.py`/`runner.py`/`finalizer.py` 零改动；`session_lifecycle.py` 的 16 个 hunk 均不在 `_teardown` / `_delete_session_reporting` 函数体内（fork marker 落点与上游 hunk 不重叠） |
| fork 对旧术语的引用 | `src/chrys/*/aixcoding/` 与 `aixcoding/` 下 `.py` 对 `project_root`/`--project`/`source_kind` 引用均为 0 |
| 批次1 实现对 cwd 的依赖 | `notice`/`reader`/`analyzer` 均不读 cwd/project/workdir，定位靠 `session_id`+`logical_turn_id`+`pass_id` |

## 4. 与已定方向的交叉点

- **N9 公共字段**：projectName/cwd 取「当前轮 live workspace」本就是定案（`nodes/runtime-context.md`）。按 ID 恢复使「进程启动目录 ≠ 会话工作目录」成为常态入口，该定案从"修旧缺陷"升格为"正确性前提"。
- **L-D03**（defect-register）：旧版无 workspace 时回退进程 cwd 生成 projectName/Git 是缺陷，本就要修；0.37.0 让不修就会产生错误数据。
- **BR-8 撤销理由的延伸**：上报协议面向多个 AI 工具，不跟随 iCode 内部术语。`projectName` 是协议字段，不应随上游 `project`→`workdir` 改名而改。
- **批次2（N7）**：上游已改 `app/acp/server.py`、`app/acp/session_manager.py`、`app/acp/history.py`（+249 行），批次2 接缝需在 0.37.0 上重定位。

## 5. 需要跟进的事项

1. **批次1 升级后复跑**：V1–V3 判别结论与全部 telemetry 测试需在升级基线上复验。V3 尤其——v0.36.0 改了 `service/trajectory/compaction.py`（+145 行）并新增 `COMPACTION_THRASH_DETECTED`、`PROMPT_CACHE_MISSED` 事件类型与 `CompactionSkipReason.NOTHING_FREED`（属 0.36.0，升级到 0.37.0 会一起进入）。
2. **批次2 在 0.37.0 基线上开工**：上游已改 ACP 三文件，避免在 0.35.2 上写接缝再合并。
3. **批次3 公共字段**：projectName、Git、cwd 必须取 live session 的 workspace（`primary_cwd`/`working_dirs`），不取进程 cwd。
4. **升级本身**：不可降级；升级前关闭全部实例、备份配置目录与独立存放的 session 目录。

## 6. 分析边界与未验证事项

- 未做 `merge-tree` 三方模拟，未在 0.37.0 上跑测试；「无冲突」按 hunk 位置推断。
- `on_session_restore` 完整 diff 只看了 hunk 头与片段；N7 的 live-history 选择在 0.37.0 上是否仍正确未验证。
- web_fetch 得到的 release notes 是模型摘要，已以源码为准核对「会话文件迁移」与「恢复会话默认用保存工作目录」两条关键描述。
- 附带观察（非 telemetry 特有）：fork 相对 v0.35.2 改过的 80 个上游侧文件中，33 个上游在 v0.35.2..v0.37.0 也改过（含 `app/acp/server.py`、`app/acp/session_manager.py`、`tests/architecture/trajectory_wait_manifest.json` 等），属升级通用冲突面，具体处置走 UPGRADE-RUNBOOK。
