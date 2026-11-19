# 任务清单：模型配置恢复官方可编辑

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。

## 状态

评审处置轮（2026-11-19）：治理落账已提交推送（43f1ff84，PR #135，CI 全绿）；
批次综合评审 + Peer Review（PEER-REVIEW-HOWTO 口径）均已完成——代码面通过，
处置三件已落地（待办 1 手册措辞 / finding-2 活文档更新）。**当前 blocker =
finding-1：catalog-sync 责任人周彬对 catalog-sync/design.md 的 R10 重签**
（正文修订十五+退役迁移超"R2 类正文修正"豁免）；重签后 PR reopen 合并。

## 待办

- [x] 实现：入口恢复（F4/picker/indicator/read_only，4 文件回官方 + 门限恢复）
- [x] 实现：管理列表过滤 + 选中兜底 + 删/存拒绝（models/screen.py）
- [x] 实现：ACP write/delete 拒绝门禁（session_manager.py）
- [x] 实现：判定函数 `server_owned_profile_ids`/`is_server_owned_profile_id`
- [x] i18n：`tui.model_config.server_managed` 新 key（zh 译文）+ read_only_notice
      官方文案回归 + oracle 登记；extract/update/compile/check 四连
- [x] 测试：`test_read_only_gate.py` 重写（9 用例）；上游 5 测试文件回官方；
      ACP 拒绝用例 ×2
- [x] 手册：zh+en 模型章恢复"配置模型"+ 旧口径清扫（10 文件 + $ 符号修正 2 处）
- [x] 真机验证：F4 过滤/切换可用/自建增删改/忙只读六项（用户签认通过）
- [x] 首轮提交：d07c5d43（功能 17 文件）/ 6ac0bc3f（手册 10）/ 1eb09dc7（$ 修正）
- [x] CI 首红复盘：gen 孤儿 12 / R2 ×3 / R3 ×4 / ty ×1 本地全复现
- [x] 修复：ty 全量（`str()` 包装）；R3 marker ×4 文件 10 处（C174-C180）
- [x] 修复：catalog-sync design 登记表迁移（12 点退役注记 + 修订记录十五）
- [x] 六件套落盘（本批 model-config-restore）
- [x] 责任人签认 design.md / self-review.md（赵阔，2026-11-18；日期格式规范化一处非内容改动）
- [x] 签认后复验：gen --strict OK（159 marker/19 retired/0 warning）/ R2 R3 仅剩本地
      未跟踪启动脚本 / closure OK / 定向 319 过
- [x] core 范围基线对照：7 失败中 6 个基线固有（659b56ef 复跑实证）、1 个环境
      缺件，均与本批无关（verification §4a）
- [x] 治理落账提交推送（43f1ff84：marker/六件套/catalog-sync 迁移/ty 修复，
      PR #135 CI 全绿）
- [x] 综合评审 + Peer Review 处置（2026-11-19）：待办 1 手册"至少保留一项"
      措辞对齐实现（zh/en models.md + 桌面版）；finding-2 活文档更新（本文件
      状态节 + verification §2）；待办 2（竞态克隆得自建副本）留档不处理、
      待办 3（链接校验工具沉淀）不做、finding-3（预估"~"口径）仅记录——
      均按评审建议
- [ ] blocker：周彬对 catalog-sync/design.md 执行 R10 重签（finding-1）
- [ ] 处置提交推送 + PR #135 reopen + 裁决留痕（PR 评论）

## 挂起与备忘

- core 范围复跑已完成（2026-11-18）：24328 passed / 7 failed，7 个失败经
  基线 659b56ef 对照均与本批无关（6 基线固有 + 1 环境缺件，verification §4a）。
- `aixcoding-launch.py` 本地未跟踪（SAC 绕过脚本，历来不入库）；本地 R2/R3
  扫描会报它，CI 干净检出不涉及，不处理。
- catalog-sync design.md 修订记录（十五）与退役注记已按 environment-config
  先例格式落位；**R10 重签待 catalog-sync 责任人周彬执行**（finding-1，
  2026-11-19 Peer Review 提出——本文件曾误写"随本批签认一并完成"，当日更正）。
- 竞态克隆下发模型得到自建副本：设计内行为（综合评审待办 2，留档不处理）；
  手册链接校验工具沉淀：非本批义务（待办 3，不做）。
