# 需求：模型配置恢复官方可编辑（下发只读隐藏、自建全量可管）

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

catalog-sync 批次（PR #85）将模型管理定为"恒只读 + 入口隐藏"：F4 绑定删除、
picker"管理模型…"条目删除、`/models` 恒只读、指示器标签改活注册表取值。产品
需求变更为与官方 0.35.2 一致的可配置化，同时保留服务端目录的管理权：管理员
下发的模型用户不能动，用户自建的模型完全自管。

前置依赖：catalog-custom-coexist 批次（PR #132）已在磁盘与同步层实现下发/
自建共存（`synced_from_server` 标记、只删服务器收回的下发档案、自建永不
触碰、id 撞车服务器胜出）——本批在其上补界面与写路径侧。

## 目标与非目标

- 目标：
  1. 入口恢复官方 0.35.2：F4 / picker"管理模型…" / `/models` / 指示器
     configure，四处全部回到官方行为；只读条件恢复官方"轮次运行中才只读"。
  2. 管理界面只列自建模型：下发模型不出现在 `ModelConfigScreen` 侧栏。
  3. 下发模型不可改删：管理界面删除/保存、ACP 写入/删除四条路径遇到下发
     档案一律拒绝并提示"服务端统一管理"。
  4. 自建模型全量可管：新建、克隆、编辑、删除（官方原生能力恢复）。
  5. 指示器恢复官方快照语义（catalog-sync 的活注册表标签定制退场）。
  6. F8 用户手册同步：模型章恢复"配置模型"（zh+en），旧口径（仅切换/管理员
     分配/联系管理员调窗口）全清。
- 非目标（防止范围蔓延）：
  - 不改同步语义（`apply_catalog`/`_publish`/标记契约全部属 coexist 批次）。
  - 不改 auto_sync 三态开关与 `is_catalog_managed()` 粘滞判定。
  - 不给 `ModelProfile`/schema/loader 加字段（沿 coexist 零上游字段裁决）。
  - 下发模型仍出现在切换列表（picker/`$`）供选用——仅管理界面隐藏。

## 用户场景

1. 登录后按 F4：看到自己创建的模型列表；管理员下发的模型不在列表中，
   可新建/克隆/编辑/删除自建模型。
2. 切换模型（状态栏/`$`）：下发与自建模型都在，均可选用。
3. 轮次运行中打开配置界面：只读 + "智能体正在运行"官方提示（官方行为）。
4. 同步在配置界面打开期间落盘：侧栏虽陈旧，对下发档案的删除/保存仍被拒绝。
5. ACP 客户端试图改/删下发模型：收到 "managed by the server catalog" 错误。
6. 服务器收回某下发模型：下轮同步删除本地档案（coexist 语义），管理界面
   与切换列表随之消失；自建模型不受影响。

## 验收标准

- [ ] F4 绑定、picker manage 条目、`read_only=self._config_read_only()`、
      `model_indicator.py` 与官方 v0.35.2 逐文件一致（或 diff 仅剩本批登记点）。
- [ ] `ModelConfigScreen._listed_profiles()` 过滤下发 id；`on_mount` 默认选中
      兜底（默认模型可能不在侧栏）。
- [ ] `_do_delete`/`_save_only` 对下发档案抛 `ConfigError`；ACP write/delete
      对下发 id 抛 `AcpSessionError`。
- [ ] 判定函数与同步同源（读标记），`.catalog-state.json` 不参与。
- [ ] 上游 5 个测试文件恢复官方版；`test_read_only_gate.py` 重写为新契约；
      ACP 拒绝用例 2 条；oracle 清单含 `tui.model_config.server_managed`。
- [ ] 手册 zh+en 模型章与 0.35.2 基准一致 + 定制边界小节；全库链接 0 坏、
      无 iCode 残留、zh↔en 结构对等。
- [ ] 治理门禁：`check_r2_diff` / `check_r3_markers` / `gen_customizations
      --strict` / `check_docs --closure` / ty 三平台 / ruff 双检全绿。

## 开放问题

- 无（展示层"完全不显示"vs"置灰"已由产品拍板为前者，2026-11-18）。
