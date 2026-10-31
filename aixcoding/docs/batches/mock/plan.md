# 任务清单：mock 基建迁入

> 活文档（AI 维护，不签认）。续接入口：当前状态、下一步、挂起事项。AI 每次接手先读本文（DEVELOPMENT.md §4 第 1 步）。

## 状态

**全部完成**（2026-10-26）：本地门禁全绿（pytest 158 passed + 2 skipped / ruff /
format / import 边界 / check_docs）+ 双 AI 评审闭环（blocker 清零 + 增量复审通过）+
CI 绿（PR #56 checks，两轮）。CI 证据按 DEVELOPMENT.md §7 以 PR checks 为源，
不回写仓库。

## 待办

（无——下方清单全部勾选完成。）

- [x] design.md 负责人签认（R10，2026-10-25）
- [x] ADR-0009 负责人签认（R10，2026-10-25）
- [x] 建 `aixcoding/mock/` 骨架：包根 `__init__.py` + `__main__.py`（launcher）+ `README.md`（M6 改写）
- [x] M1 auth 迁入 + 最小契约测试 `test_auth_server.py`（3 用例：设备码信封 / 轮询状态 / user_info 怪癖）
- [x] M2 update 迁入 + 契约测试迁入 `test_update_server.py`（import 改名 + 文件级 noqa）
- [x] M3 model_catalog 迁入（内嵌 auth import 改名、包内绝对导入、hack `parents[3]`、`config_new.json` 零改动核验）+ 契约测试与 `direct_route` 夹具迁入
- [x] update CLI 补 `--port` 参数（docstring 与 main 同步更新）
- [x] launcher 冒烟：`--list` / 默认组合起停探测 / 端口占用 fail-fast（exit 1 + netstat 提示）/ 互斥检查（exit 2）；Ctrl+C 路径留日常联调自然验证
- [x] 全量门禁：`pytest aixcoding/tests` 绿 + ruff check/format `aixcoding/` + `check_import_boundaries.py`
- [x] CI（aixcoding-tests.yml）全绿（PR #56 checks，两轮；证据以 PR checks 为源不回写仓库）
- [x] 产出 self-review.md + verification.md（self-review 负责人已确认 2026-10-26）

## 挂起与备忘

- M4（telemetry-mock）随 telemetry 殿后（ROADMAP §2 阶段三；`batches/restructure/plan.md` §3 已注记）；
- env 更名 `AIXCODING_AUTH_*` 归 auth 特性迁入执行（ADR-0009；本特性不改名，联调配方用现名）；
- catalog 对拍测试 skipif 自动恢复（design 假设 1 降级预案生效：`parse_catalog` 消费方未迁入，`chrys.service.profiles.models.catalog` 落地后自动解除 skip，届时断言细节随消费方特性 design 重核）；
- 旧分支 catalog 测试与实现本就不配套（5 个断言锚旧一代 version/items 形态），迁入时以实现为准重写——wire 契约以现行 mock（服务端原生 models 形状）为准，不再回溯旧实现。
