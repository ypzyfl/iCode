# 验证记录：模型配置恢复官方可编辑

## 1. 静态与门禁（本机，2026-11-18）

| 检查 | 结果 |
|---|---|
| ruff check / format --check（改动文件） | 全绿 |
| ty check --error-on-warning src/chrys（全量，三平台口径同 CI core） | 首红 1（session_manager `object`→`str`）→ 修复 → **全绿** |
| i18n extract/update/compile/check 四连 | 全绿（升版后 POT 头过期一次，重跑刷新） |
| oracle（test_catalog_oracle 3 用例） | 3 passed |
| gen_customizations --strict | 首红 12 孤儿（catalog-sync 登记未退）→ 迁移落位 → 签认后复验（见 §4） |
| check_r2_diff / check_r3_markers | R2 首红 3 未批准文件 / R3 首红 4 文件无 marker → marker ×10 + R2 表落位 → R3 仅剩本地未跟踪的 aixcoding-launch.py（CI 干净检出不涉及）；签认后复验（见 §4） |
| check_docs --closure | 六件套落位前已 OK（27 ADR/47 design）；落位后随签认复验 |

## 2. 测试（本机）

- 定向子集（catalog + models/picker/indicator/footer/bindings + ACP + oracle +
  branding）：343 passed / 2 skipped，0 失败。
- 大回归（tests/app/tui/screens + tests/app/acp + tests/foundation/i18n）：
  4626 passed / 42 skipped / 2 failed，**两失败均与本批无关**：
  `test_exit_does_not_join_a_running_count`（时序偶发，单测复跑即过）；
  `test_chrys_acp_sub_agent_bridges_card_...`（需 venv 内 chrys.exe 入口，
  本机纯 pytest 环境缺件，改动前同样跑不了）。
- core 范围并行复跑（tests 除 architecture/app/tui，对应 CI core shard 的
  pytest 半）：24328 passed / 7 failed，失败逐项甄别与本批无关——结果与
  基线对照证据见 §4a。

## 3. 真机手工验证（用户执行并确认通过，2026-11-18）

| # | 操作 | 结果 |
|---|---|---|
| 1 | F4 打开配置界面 | 通过（入口恢复） |
| 2 | 列表不见下发模型 GLM-5.3 (server) | 通过（过滤生效） |
| 3 | `/models` 切换列表含下发模型并选用 | 通过 |
| 4 | 选中下发模型发消息 | GLM 正常回复（连通） |
| 5 | 自建模型新建/编辑/删除 | 通过 |
| 6 | 轮次运行中 F4 只读提示 | 通过（官方行为） |

测试材料：下发档案 `%APPDATA%\chrys\models\srv-glm-5-3.yaml`（带
`synced_from_server: true`，智谱 Anthropic 端点）；预检=标记识别/加载器忽略
未知键/可选性三断言通过。

## 4. 签认后复验（责任人赵阔 2026-11-18 签认 design/self-review 后）

- [x] gen_customizations --strict：**OK**——111 登记行 / 159 marker / 20 design /
      19 retired id / 0 warning（C174-C180 生效，catalog-sync 孤儿消零）
- [x] check_r2_diff / check_r3_markers：仅剩本地未跟踪 `aixcoding-launch.py`
      （CI 干净检出不涉及），其余全过
- [x] check_docs --closure：**OK**（签认日期格式规范化 20261118→2026-11-18，
      签认内容零改动）
- [x] 定向子集复跑：319 passed / 0 failed

## 4a. core 范围基线对照（与本批无关性的证据，2026-11-18）

CI core shard pytest 半（tests 除 architecture/app/tui）本机并行：24328 passed /
7 failed。7 个失败逐项甄别：

| 失败 | 判定 | 证据 |
|---|---|---|
| chrys_in_chrys 子智能体桥接 ×1 | 环境缺件 | venv 无 chrys.exe 入口，改动前即跑不了 |
| analytics 内存驻留校准 ×3、git_head 截止期 ×1、operation_close ×1、injection 元数据 ×1（并行挂/单跑过） | 基线固有 | **基线 659b56ef（无本批任何改动）单跑同集合：4 failed**——与本批无关 |

## 4b. 官方基线锚点（独立评审 2026-11-19 提示，防误用）

"恢复官方 v0.35.2"的对照基线 = 上游对象 **`2fd777f6`**（追上游合并 c93336ee 的第二父，
`pyproject.toml` version="0.35.2" 已核）。**本地 `v0.35.2` tag（e0316c1c）是 fork 定制 tag**
（2026-11-17 主干状态，含 catalog-sync 定制）——用它做 diff 会方向性误判（会显示"上游带
AIxCoding marker"）。恢复归零核验统一用：`git diff 2fd777f6 -- <file>`。

## 4c. C134-C138 恢复（独立评审 2026-11-19 处置轮）

- 四个测试文件（deletion / prompt_shortcut_send / manual_reload / reload_profiles）
  与 `2fd777f6` **diff 完全归零**（去 skip + 去 marker 注释 + 还原上游参数表）。
- 恢复的 5 个测试实跑全过（deletion 四参数化场景、manual_reload 两流、
  reload_profiles 编辑器重建流、prompt_shortcut models 参数）；目录隔离由
  tests/conftest.py 会话级 pinned config dir 天然覆盖（`catalog_directory()` 落
  空临时目录，无需逐测试 stub——独立评审报告的该项担忧经核实已由既有机制兜住）。

## 5. CI 首轮 12 失败复盘（PR #135，2026-11-18）

| 根因 | 挂的 checks | 处置 |
|---|---|---|
| gen --strict 孤儿登记 ×12 | AIxCoding quality gate | catalog-sync 12 点迁退役记录（本批 design 持有墓碑） |
| R2 未批准上游文件 ×3 | quality gate / govern | 本批 R2 表登记 3 行 |
| R3 无 marker ×4 文件 | quality gate / govern | marker ×10（C174-C180） |
| ty 全量 1 诊断 | ci / Test 三平台 core shard | `str()` 包装修复，全量转绿 |
| 上游 pytest core 失败 | ci / Test 三平台（ty 同 shard） | ty 修复消除一半；pytest 半本地并行复跑核验中 |
| 其余 5 项 | upstream gate / shards / guard hooks | 均为上述失败的级联（gate 校验矩阵结果） |
