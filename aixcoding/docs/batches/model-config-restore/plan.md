# 任务清单：模型配置恢复官方可编辑

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。

## 状态

CI 修复批（治理补账）：PR #135 首轮 12 checks 失败根因（gen 孤儿 12 /
R2 unauthorized 3 / R3 marker 缺 4 / ty 全量 1）已逐项落地修复，六件套就绪，
**待责任人签认 design.md 后复验门禁、一次提交推送**。

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
- [ ] 一次提交推送（含 marker 注释、ty 修复、六件套、catalog-sync 迁移）

## 挂起与备忘

- CI `ci / Test` 三平台 pytest 侧：本地 core 范围（tests 除 architecture/
  app/tui）并行复跑进行中；ty 侧（core shard 的另一半失败原因）已修复转绿。
  复跑若再有失败，处置后随本批一并提交。
- `aixcoding-launch.py` 本地未跟踪（SAC 绕过脚本，历来不入库）；本地 R2/R3
  扫描会报它，CI 干净检出不涉及，不处理。
- catalog-sync design.md 修订记录（十五）与退役注记已按 environment-config
  先例格式落位，R10 重签随本批签认一并完成。
