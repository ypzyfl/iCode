# 设计：模型配置恢复官方可编辑——下发模型只读隐藏、自建模型全量可管

<!--
签认规则（R10 · 决策档）：责任人本人编辑本头部（状态→已确认、填责任人与日期，
确认意见可选），AI 不得代填。签认后修改正文需重新签认（R2 类正文修正除外，
须在正文原位加注记并标注不触发重签）。
-->

- 责任人：赵阔
- 状态：已确认
- 确认日期：2026-11-18
- 确认意见：无

## 方案概述

catalog-sync 批次的"恒只读 + 入口隐藏"政策取消：模型管理界面恢复与官方
0.35.2 一致的可配置化（F4 / picker"管理模型…" / `/models` 三入口、轮次运行中
才只读），叠加本定制的边界——**服务端目录下发的模型（带
`synced_from_server: true` 标记，判定与共存语义由 catalog-custom-coexist 批次
承载）不出现在管理列表、四条写路径拒绝改删；用户自建模型新建/克隆/编辑/删除
全量恢复**。

```
管理界面（ModelConfigScreen）
  ├─ _listed_profiles()：按 server_owned_profile_ids() 过滤下发档案（C175）
  ├─ on_mount 选中兜底：全局默认模型可能是下发的，不在侧栏时选第一个自建（C176）
  ├─ _do_delete/_save_only：目标为下发档案 → ConfigError 拒绝（C177，陈旧侧栏防线）
  └─ 只读条件：恢复官方 self._config_read_only()（轮次忙才只读），官方文案回归
写路径门禁（防旁路）
  ├─ ACP write_model_profile/delete_model_profile：下发 id → AcpSessionError（C178）
  └─ 判定函数（定制包内）：server_owned_profile_ids()/is_server_owned_profile_id()
     （catalog.py，读 <id>.yaml|.yml 的标记，与同步判定同源）
```

## 关键机制与不变量

1. **入口与只读语义零定制**：F4 绑定、picker manage 条目、model_indicator、
   `read_only` 门限、`_READ_ONLY_NOTICE` 文案全部回到官方 v0.35.2 形态
   （`model_indicator.py` 整文件回官方；catalog-sync C035-C049 相应点退役）。
2. **下发/自建判定与同步同源**：判定只认 YAML 标记（coexist 批次契约），
   不引入第二事实源；`.catalog-state.json` 不参与（沿 coexist 裁决）。
3. **界面过滤是展示层，写路径门禁是安全层**：管理列表过滤之外，删除/保存/
   ACP 写删各自独立查标记——侧栏陈旧（同步在界面打开期间落盘）时仍拒绝。
4. **同步语义零改动**：coexist 的"只删有标记且服务器收回的文件、自建永不
   触碰、id 撞车服务器胜出"整体不动；本批不碰 `apply_catalog`/`_publish`。
5. **ACP 拒绝语义**：与本地删除同因（服务端资产，仅服务器可收回），报错文案
   "managed by the server catalog"，不泄露同步细节。

## 上游改动清单（R2）

> 节标题须保持机器可解析的标准形态（`check_r2_diff.py` 全等匹配本节标题）。
> 每行"归属结论"回答 R1 细则二之问："这行能挪进 `src/chrys/service/aixcoding/` 吗"。

| # | 文件 | 改什么 | 预估行数 | 标记注释位置 | 归属结论（逐行） |
|---|---|---|---|---|---|
| 1 | `src/chrys/app/acp/session_manager.py` | `write_model_profile`/`delete_model_profile` 两方法插入下发档案拒绝门禁（lazy import 判定 + `AcpSessionError`，各 ~5 行；write 侧实参 `str(...)` 包装满足 ty） | ~+10 | 两处拒绝块（marker ×2，C178） | ACP 会话写入面属上游 session manager；判定函数在定制包，门禁必须落在写入现场，无法外置 |
| 2 | `tests/app/acp/test_session_manager_profiles.py` | 两条拒绝契约测试（write/delete 各一，monkeypatch 判定函数，不触网不落盘） | ~+26 | 两测试定义处（marker ×2，C179） | 上游测试文件；契约测试与被测面同库是仓库惯例 |
| 3 | `tests/foundation/i18n/_profile_config_catalog_oracle_ids.py` | `tui.model_config.server_managed` 条目 +1（附注释行） | +2 | 条目处（marker ×1，C180） | oracle 清单是上游 i18n 门禁数据面，新 key 须同 commit 登记（catalog-sync C042 先例同款） |

其余上游文件改动均为**恢复官方 v0.35.2 形态**（F4/picker/indicator/read_only/
5 个上游测试文件），与官方基线 diff 归零或缩减，已属 catalog-sync R2 表
批准文件的回归，不新增登记；`locales` 产物随 msg 定义自动产生（同 catalog-sync
12 号豁免形态）。

## 定制点登记预告

> 点级登记（ADR-0015）：匹配键=(落点, marker 锚)；id 自 C174 起（`--report`
> 实测当前最大 C173）。实施后 `--strict` 对账为门禁。

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
|---|---|---|---|---|---|---|
| C174 | src/chrys/app/tui/screens/models/screen.py | AIxCoding catalog: server-managed notice wording | 1 | `_SERVER_MANAGED_NOTICE` msg 定义（fallback + po msgstr） | 低 | 〔政策变更〕下发模型允许本地改删时随组退役 |
| C175 | src/chrys/app/tui/screens/models/screen.py | AIxCoding catalog: sidebar hides server-owned profiles | 1 | `_listed_profiles()` 过滤 + `server_owned_profile_ids()` 读取 | 低 | 〔政策变更〕管理列表重新纳入下发模型时退役 |
| C176 | src/chrys/app/tui/screens/models/screen.py | AIxCoding catalog: default selection skips server-owned entries | 1 | `on_mount` 的 `listed_ids` 兜底选择 | 低 | 〔随组〕随 C175（列表不过滤时兜底自然消失） |
| C177 | src/chrys/app/tui/screens/models/screen.py | AIxCoding catalog: delete/save refuse server-owned profiles | 2 | `_do_delete`/`_save_only` 两处拒绝块（陈旧侧栏防线） | 中（写路径防线） | 〔政策变更〕随 C174；或 coexist 标记机制退役时整体重设计 |
| C178 | src/chrys/app/acp/session_manager.py | AIxCoding catalog: ACP write/delete refuse server-owned profiles | 2 | write/delete 两方法拒绝门禁 | 中（写路径防线） | 〔政策变更〕同 C177 |
| C179 | tests/app/acp/test_session_manager_profiles.py | AIxCoding catalog: ACP refusal contract tests | 2 | 两条拒绝契约测试定义 | 低 | 〔随组〕随 C178 |
| C180 | tests/foundation/i18n/_profile_config_catalog_oracle_ids.py | AIxCoding catalog: server_managed oracle entry | 1 | `tui.model_config.server_managed` 条目 | 低 | 〔随组〕随 C174 |

> 定制包 `src/chrys/service/aixcoding/models/catalog.py` 的两个判定函数与
> `aixcoding/tests/catalog/test_read_only_gate.py` 重写、`aixcoding/manual/`
> 手册 10 文件为独立定制模块/开发资产，无上游落点，不入登记表（ADR-0015 射程）。

### 退役记录

> 承接自 catalog-sync（2026-11-18 本批实施）：其"恒只读 + 入口隐藏"政策取消，
> removal_condition 预写的〔政策变更〕/〔随组〕条件成立，现役行删除、id 墓碑化
> 永不复用；原 design 保留指向注记并由责任人按 R10 重签。

| id | 原落点 | 退役日期 | 依据 |
|---|---|---|---|
| C035 | src/chrys/app/tui/screens/main/config_actions.py | 2026-11-18 | 恒只读政策取消：`read_only` 恢复官方 `_config_read_only()` 门限 |
| C036 | src/chrys/app/tui/screens/main/screen.py | 2026-11-18 | F4 入口恢复官方绑定 |
| C037 | src/chrys/app/tui/screens/main/screen.py | 2026-11-18 | 指示器恢复官方快照标签（`model_registry` 接线摘除） |
| C038 | src/chrys/app/tui/screens/models/picker.py | 2026-11-18 | picker"管理模型…"条目恢复官方（文件整体回官方） |
| C040 | src/chrys/app/tui/screens/models/screen.py | 2026-11-18 | `_READ_ONLY_NOTICE` 恢复官方"智能体正在运行"文案（本批 C174 接替新提示） |
| C041 | src/chrys/app/tui/screens/main/model_indicator.py | 2026-11-18 | 文件整体回官方 v0.35.2 |
| C044 | tests/app/tui/screens/test_model_picker.py | 2026-11-18 | 文件恢复官方版，反断言随之撤除（其 removal_condition 预写） |
| C045 | tests/app/tui/screens/test_model_picker.py | 2026-11-18 | 同 C044：manage 入口恢复，还原真实选项驱动 |
| C046 | tests/app/tui/screens/test_model_indicator_wiring.py | 2026-11-18 | 文件恢复官方版，registry 名对齐构造回改（预写条件） |
| C047 | tests/app/tui/screens/test_model_config.py | 2026-11-18 | 文件恢复官方版，notice 断言回改（预写条件） |
| C048 | tests/app/tui/behaviors/test_chrys_footer.py | 2026-11-18 | 文件恢复官方版，F4 footer 期望回补（预写条件） |
| C049 | tests/app/tui/i18n/test_bindings.py | 2026-11-18 | 文件恢复官方版，f4 声明回补（预写条件） |

## 风险与最坏情况

- **标记丢失即防线退化**（coexist S1 既知限制，本批叠加面）：外部重写档案文件
  丢标记 → 判定视作自建 → 可编辑可删除；方向保守（不误拒用户），服务器侧
  下轮同步会以新档案对齐。留档不修，与 coexist 同一裁决。
- **管理列表与切换列表不一致是设计而非缺陷**：同一档案在 picker 可见、在管理
  界面不可见；手册"模型的来源"小节已写明边界，避免用户误判"模型丢了"。
- **回滚**：revert 本批提交即回到恒只读；官方形态回归无数据迁移（标记仍由
  同步维护），catalog-sync 的 C030/C031/C034（registry 锁/快照/启动接线）
  不受影响、无需回滚。

## ADR 判定

1. 有被认真考虑但否决的备选方案？——有：管理列表"置灰只读"展示下发模型
   （产品拍板改为完全不显示）；判定源用 `.catalog-state.json`（coexist 批次
   已否决，本批沿用其裁决）。属模块内实现选择，理由留档于上。
2. 撤销代价高？——否，见风险节回滚。
3. 约束未来工作模式？——否，机制自包含（判定函数 + 过滤 + 拒绝），docstring
   与本文已承载。
4. 依赖上游非公开接口或行为？——否，`server_owned` 判定仅读 coexist 契约的
   公开标记；恢复的入口/只读语义即官方公开行为。

四问均不触发，不出 ADR。
