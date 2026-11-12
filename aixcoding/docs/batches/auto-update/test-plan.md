# 测试计划：TUI 自动更新流程（auto-update）

> 活文档：随时更新、不签认；测试方案随 design 签认生效。

## 覆盖矩阵（验收标准 → 测试入口）

| requirements 验收 | 测试入口（文件::用例组） | 类型 |
|---|---|---|
| 检测契约（四参数/200/204/304/400/forceUpgrade/garbage） | `test_client.py`（mock server 测试桩真起） | 契约 |
| tier 与 `[update].base_url` 优先级 | `test_client.py` | 契约 |
| 15s 总超时不变量 | `test_client.py`（slow 模式 + 时钟断言） | 行为锚定 |
| 24h 节流 / 同日去重 / 跳过持久化 / 新版本恢复 / 双临时文件读取（计数行数/mtime/标记） | `test_state.py`（时钟注入；`now` 固定本地当天中午，修订十五——避免 00:00–01:00 跨午夜误红） | 单元 |
| 失败计数闸（计数 ≥3 → 建标记+删计数+通知+跳过；标记今日 → 全天不检查；非今日 → 重置正常弹） | `test_flow.py` | 单元 |
| 弹框三选项 + 强更单选项不可取消（Esc/backdrop） | `test_dialog.py`（Textual pilot） | 行为锚定 |
| gate 矩阵（开关/CI/serve/pytest/SOURCE） | `test_flow.py` | 单元 |
| 缓存重显判定与状态迁移 | `test_flow.py` | 单元 |
| wrapper 命令 per-OS 构造（等待前缀/失败追加序/零删除操作/relaunch） | `test_runner.py`（非当前平台 skipif，R13 见 design §10） | 契约 |
| 等待-执行-重启序（端到端） | `test_runner.py`（假命令写标记文件）+ Windows 实机冒烟 | 集成+手工 |
| 上游零回归 / strict 零漂移 | `pytest aixcoding/tests` + `gen_customizations --strict` + Smart Test | 门禁 |

> 2026-11-12 补记（design 修订十八）：`test_client.py` 的
> `test_tier_bases` 中 local 期望改为 `http://127.0.0.1:7778`
> （无 `/csas`），三处 mock 夹具 `_point_at` 不再补前缀；
> `test_update_server.py` 全部用 `RELEASE_ROUTE` 常量构造 URL，
> 随 `API_PREFIX` 自动跟随、无需改动。dev/prod 期望值与显式
> `base_url` 覆盖用例均不变（部署前缀保留）。手工冒烟 1 的
> 「local tier + mock」口径不变，仅端点路径少一层 `/csas`。

> 2026-11-12 补记（design 修订十七，活文档追加）：上表「弹框三选项
> + 强更单选项不可取消（Esc/backdrop）」扩张为**两种变体统一严格
> 模态**。`test_dialog.py` 现覆盖：普通版三选项、强更单选项、
> `test_escape_does_not_close_either_variant`（两种变体按 Esc 后
> `answers == []` 且弹框仍在）、
> `test_backdrop_click_does_not_close_either_variant`（两种变体
> `dismiss_on_backdrop is False` + `pilot.click(offset=(0,0))` 后
> 不产生回答）、按钮回答与重复 dismiss 恰好一答。手工冒烟 2
> 「强更单选项 + Esc/点击外部不关」仍成立（单选项实测已做）；
> 新增冒烟口径：普通版本按 Esc / 点击外部同样不关，只能经按钮退出
> （design 修订十七，待责任人实机复核）。本批 R13 豁免清单仍为
> 2 类，未新增。

## 关键夹具

- **mock server 桩**：`from aixcoding.mock.update.server import MockUpdateConfig,
  create_server`，`port=0` 起随机端口；`/debug/config` 切模式（update/no_update/
  error/garbage/force_update/force_upgrade/drop_fields/slow_ms）——README 契约全覆盖；
- **状态隔离**：`config_dir=tmp_path`（aixcoding/tests conftest 同构）+
  `state._now` 时钟注入；
- **gate 注入**：`monkeypatch.setenv/delenv`（CI / PYTEST_CURRENT_TEST /
  AIXCODING_ENVIRONMENT）+ flavor stub；
- **假更新命令**（修订八形态）：`file://` 假安装脚本（成功 `echo ok` / 脚本
  `exit 1` / 下载目标不存在三条路径），断言执行顺序与失败计数。

## 平台豁免（R13）

- `test_runner.py` Windows 专属命令构造断言：`skipif(sys.platform != "win32")`——
  被测 `cmd /c` 序列语义依赖 Windows 真实 console 行为，跨平台 shell 不能等效；
  批准指向＝design.md 签认（与 internal-installer POSIX skip 同构，就地注释留痕）。
- POSIX 侧同构 `skipif(sys.platform == "win32")`。
- 本批 R13 豁免共 2 类（R13 ②类 lint：C173 `pyproject.toml` 目录级条目；
  R13 ③类测试：本节平台 skipif）。`self-review.md` R13 项已追加补记汇总
  两类；PR 变更导览「新增豁免清单」须逐条列 2 条（见 plan.md 待办）。

## 手工冒烟（verification.md 落证据）

1. local tier + mock `{"version": "999.0.0"}` → 启动弹框 → 三选项逐项；**已做**
   （2026-11-11，含"下次提醒"下次启动再弹、"跳过此版本"持久化实测）；
2. `force_upgrade=true` → 单选项，Esc/点击外部不关；**已做**（单选项实测）；
3. 假更新命令替身 → 立即更新 → 观察退出-执行-relaunch（含 `-s` 恢复会话）；
   **失败路径已做**（退出→wrapper→失败提示→不重启→计数，debug.log 实测
   0.3s 自动退出）；成功 relaunch 由 file:// e2e 覆盖（真实镜像 404 下不可达）；
4. 假命令 `exit 1` → 失败提示且不重启，失败计数文件追加一行；**已做**（含
   修订十条件式提示行实测）；
5. 连续 3 次失败后启动 → 创建 skip-today 标记、删除计数文件、通知"今日跳过、
   明日再试"，当日后续启动全天无检查；删除标记重启 → 立即恢复；**已做**（含
   通知路径指向 skip-today 的修复实测）；
6. 弹框键盘：Tab/方向键切换 + 聚焦实心高亮随焦点移动；**已做**（修订十二
   终审通过，2026-11-11）；
7. 弹框时机：引擎构建完成后立即出现（修订十三两阶段等待）；**已做**；
8. Windows 实机同 1-5。**待做**（命令串断言由 CI 覆盖）。
