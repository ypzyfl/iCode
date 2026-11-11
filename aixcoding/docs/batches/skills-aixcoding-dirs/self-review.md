# 自评审记录：aixcoding 技能目录自动加载（skills-aixcoding-dirs）

- 责任人：李海潮
- 状态：已确认
- 确认日期：2026-11-10
- 确认意见：无意见
- 开发 AI：GLM-5.3 / CodeBuddy
- 评审 AI：GLM-5.3 / CodeBuddy 子代理（独立会话，只读评审，两轮）

> 记录档：签认一次，后续追加评审记录不触发重签。
> 批次上下文：design.md v3（已签认 2026-11-09）、批次 ADR（2026-11-09 签认、2026-11-11
> 撤销——决策并入 design「ADR 判定」节）、test-plan.md、skill-directories.md、
> verification.md（命令与输出留档）。

## 2026-11-09 评审结论：通过（两轮收敛，blocker 清零）

- 轮次：2 轮（初评 1 blocker + 6 minor + 14 项核对通过 → 全部修复 → 增量复审：修复项
  通过、新发现 3 小项 + 1 备案确认 → 全部修复，门禁复跑全绿）。
- 评审范围：工作区全量变更（8 个代码文件 + 5 个上游文档 + 4 个批次文档），对照 design
  R2 清单 1-13 与登记 C158-C171（C167-C171 为 CI 复跑补登的 docs R3 marker；C147-C157 与
  并行合入批次撞号后整体后移，重编依据 main_aixcoding_cli@9d824cb5 号段快照，见 verification 表 14）；检查项：越权、R2/R3 对名、幻觉 API、吞错边界、Windows
  路径语义（symlink/junction）、测试有效性、上游测试影响面、文档与代码一致性。

### 第一轮 blocker 处置（1 条，已修复并经复审确认）

- B1 机制回归测试缺失：design/test-plan/ADR 三处共同承诺的
  「`platform.aixcoding_dir` 重定向后 helper 跟随」回归锚未交付——conftest 两行 patch
  被上游重构吞掉时 CI 不会红灯。→ 补
  `test_platform_redirect_covers_aixcoding_dir`（replace 单例 → helper 跟随、replace
  保留未指定字段、monkeypatch + 双 `cache_clear` 恢复语义干净，复审确认）。

### 第一轮 minor 处置（6 条：4 修、2 备案）

- M1 configuration.md 无可补（**备案**）：0.34 已重构信任模型段（仅描述 hooks 自身），
  design R2 #10 无落地位置——该项自然取消，上游接触面净减少；design R2 表已加实施
  备案行（`--strict` 复核通过）。此为 R2 清单收缩（减少一处上游改动），提请责任人于
  self-review 签认时追认。
- M2 junction 分叉（**修**）：Windows 目录 junction `is_symlink()` 为 False，与桌面端
  （libuv 视 junction 为 symlink）分叉 → 补 `entry.is_junction()` 跳过（3.14 pin 下
  API 可用；三平台 ty 绿）。
- M3 team 枚举错误隔离粒度（**修**）：per-entry try/except OSError，单条目损坏只跳过
  自身，兑现「单容器损坏不阻塞会话」docstring 契约。
- M4 测试落点与文档不一致（**修**）：实际落 `aixcoding/tests/skills/`（按 aixcoding/tests
  主题目录惯例，无 `service/` 层级）；design/test-plan 路径已同步（design 正文修订，
  R2 表未变，不触发重签）。
- M5 test-plan 用例名漂移（**修**）：覆盖矩阵对齐实际函数名；去重用例描述改为实际
  重叠对象（profile path × aix cwd 根）。
- M6 intellij team 根无显式断言（**修**）：`test_intellij_mirror_tree_loaded` 补
  `team-skills/ide-team` 成员断言。
- M7 design R2 #3「三处 replace」与登记表「2」不一致（**修**）：实现为两处（per-test
  fixture 复用 `_pin_config_dir`）——比预估更少；design 清单 3 措辞已同步。

### 第二轮新发现处置（3 + 1，全部已修复）

- 断言方向反转致恒真（`str(home) not in pinned`——tmp_path 在 HOME 之下必真）→ 改为
  与真实 HOME 根直接比较（首轮自写缺陷，复审捕获，如实记录）。
- design 验证命令残留旧路径 `aixcoding/tests/service/skills` → 改 `aixcoding/tests/skills`。
- design 假设 3 引用 conftest 行号漂移 → 改函数名引用。
- configuration.md 备案判断成立（复审确认 0 命中）→ design R2 #10 加备案行（见 M1）。

### 变异自证说明

- 机制回归测试的锚定层级是「字段跟随 pin」；上游侧防护由污染回归命令（verification
  矩阵 #3，本机 HOME 实存 `hanhai-h5`，64 passed）承担——两者合并构成完整防线。

### 未修项

- 无 blocker/minor 未修。两处备案（M1 configuration.md 取消、design R2 #10 备案行）
  提请责任人签认时知悉。

### 实施期自纠（如实记录）

- 定制测试首版 2 处断言缺陷（无 runtime 场景误断言 HOME 树、次序测试未 fake 上游
  `user_agents_dir`）——首跑即暴露，当场修正；
- 机制回归测试首版 `skill_paths_module` import 缺失、断言两次方向写反（tmp_path 在
  HOME 之下的路径包含关系）——均由测试失败输出直接暴露，当场修正；
- 登记表初版不符合 `gen_customizations.py` 规范（id 格式、落点列混排、except 注释
  anchor 前缀不统一）——初检 26 错，按 guard-hooks 先例格式重写后通过。
