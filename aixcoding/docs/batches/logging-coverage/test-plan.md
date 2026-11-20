# 测试方案：定制功能日志覆盖补全（logging-coverage）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

**单元测试为主**，全部落 `aixcoding/tests/` 域内既有文件追加 + 一个集中静态文件，零端到端依赖：

- **卷归属断言基础设施**：`caplog` 按 logger name 过滤（批次① `test_routing_fixes.py` 先例——公共通道断言必须按 `record.name` 前缀 `aixcoding.` / `aixcoding.detail.` 过滤，防止 root level=INFO 拦截与上游记录串扰）；detail 断言 `caplog.set_level(5)`；
- **update 失败分支注入**：复用 `test_client.py` 既有 httpx `transport` 注入设施（`client.py` 原生支持 `transport=` 参数，契约测试先例）——超时/网络错误/异常状态码/解析失败四分支参数化；
- **guard 路径注入**：复用 guard 域既有 `hooks_dir` / `asset_dir` 参数（`install_guard_hooks` 原生支持）——fresh install / 既有可合并 / 不可解析配置三形态；
- **catalog 同步**：复用 `test_catalog_sync.py` 既有 fixtures；
- **loader**：`load_config.cache_clear()` 隔离 `@cache`（既有 `test_config.py` 先例）；
- **skills**：monkeypatch `user_aixcoding_dir` / team 目录形态（既有 `test_aixcoding_skill_paths.py` 先例）；
- **mock server 不需要**：全部在 httpx transport / 文件系统层面注入；
- **上游 anchor**：零上游接触（R2 空表），无行为锚定测试义务。

测试文件组织（域内追加 + 一个集中文件）：

| 文件 | 新增内容 |
|---|---|
| `aixcoding/tests/auto_update/test_client.py` | 失败分支主通道 WARNING + 204/304 静默 |
| `aixcoding/tests/auto_update/test_flow.py` | 确认/跳过主通道 INFO |
| `aixcoding/tests/auto_update/test_runner.py` | wrapper 失败 ERROR 双写 |
| `aixcoding/tests/skills/test_aixcoding_skill_paths.py` | 成功清单 detail / 异常 detail+re-raise / FileNotFoundError 静默 / 主通道零记录 |
| `aixcoding/tests/guard/`（guard_install 既有测试文件） | 四路径通道断言 |
| `aixcoding/tests/catalog/test_catalog_sync.py` | 两处主通道 WARNING 双写断言 |
| `aixcoding/tests/config/test_config.py` | 九场景三通道参数化 |
| `aixcoding/tests/diagnostics/test_logging_coverage.py`（新建，集中） | 静态扫描（四文件零 `getLogger(__name__)`）+ startup task 三通道 + 主通道 PII 嗣兵 |

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| 1. 四文件无 `getLogger(__name__)`、域 logger 生效 | `diagnostics/test_logging_coverage.py::test_no_dunder_name_loggers`（源码扫描四文件）+ 各域用例的 name 过滤断言（生效性） | 单元（静态+路由） |
| 2a. wrapper 启动失败 ERROR 双写 | `auto_update/test_runner.py::test_wrapper_failure_error_double_write` | 单元 |
| 2b. 确认/跳过主通道 INFO | `auto_update/test_flow.py::test_confirm_and_skip_log_user_info` | 单元 |
| 2c. 检查失败主通道 WARNING（client 失败分支落点） | `auto_update/test_client.py::test_check_failure_warns_main_volume`（超时/网络/状态/解析四分支参数化） | 单元 |
| 2d. 204/304"无更新"主通道零记录 | `auto_update/test_client.py::test_no_update_204_stays_silent` | 单元 |
| 3. skills：异常 detail+re-raise / 成功清单 / FileNotFoundError 静默 / 主通道零记录 / adapter 零改动 | `skills/test_aixcoding_skill_paths.py::test_exception_detail_and_reraise` + `::test_success_paths_detail_only` + `::test_team_filenotfound_silent_permission_logged` + `::test_no_main_volume_records`；adapter 零改动由验收 9 的 git diff 核对 | 单元 |
| 4. guard：安装/失败/幂等 detail 且主通道零记录；`_replace_unparsable` 主通道 WARNING 双写 | `guard/（guard_install 测试文件）::test_install_paths_detail_only` + `::test_unparsable_reset_warns_main_volume`（含备份路径在主通道文案中的断言）+ `::test_merge_idempotent_ready_detail` | 单元 |
| 5. catalog 两处主通道 WARNING 双写；其余 detail-only 不回退 | `catalog/test_catalog_sync.py::test_overwrite_warns_main_volume` + `::test_upgrade_clear_warns_main_volume`（双写断言：主通道与 detail 同文案）；既有 detail-only 断言全量保留不回退（既有用例原样跑绿即证） | 单元 |
| 6. loader 九处与 startup task：stderr + 主通道 + detail | `config/test_config.py::test_warn_triple_channel`（九场景参数化：断言 stderr 输出、`aixcoding.config` WARNING、detail 同文案）+ `diagnostics/test_logging_coverage.py::test_startup_task_failure_triple_channel` | 单元 |
| 7. 主通道文案 PII 嗣兵 | `diagnostics/test_logging_coverage.py::test_main_channel_pii_sentinel`（触发本批全部主通道事件，断言消息不含 ehr 数字模式 / http(s):// / Traceback / 后端主机名——哨兵口径沿批次① A2 ⑤） | 单元 |
| 8. R2 空表 git diff 核对 | verification.md 落盘 `git diff --stat <上游文件清单>` 零输出 | 验证命令 |
| 9. verify --smart / aixcoding/tests / architecture 全绿 | verification.md 落盘三条命令输出 | 验证命令 |
| 10. gen_customizations --strict 0/0 | verification.md 落盘 | 验证命令 |

## 异常与降级路径

- **"无更新"与"失败"分流**（本批最关键降级断言）：204/304 必须零主通道记录（`None` 语义混合的守护断言——防止未来有人把打点挪回 `_flow` None 汇聚点，"已是最新版"被误报为失败）；
- **skills re-raise 保序**：异常打点后必须 re-raise，`adapter.py` 吞错行为零变化——断言函数仍抛出原异常（`pytest.raises` + detail 记录在先）；
- **`FileNotFoundError` 常态静默**：team-skills 目录不存在 → 零记录（detail 也不打）；`PermissionError` → 仅 detail；
- **guard 不可解析三入口**（`yaml.YAMLError` on merge / on re-parse / 非 dict 文档）均走 `_replace_unparsable` → 主通道 WARNING（三入口参数化共用断言）；
- **loader `@cache` 隔离**：九场景间 `cache_clear()`，防首场景污染；
- **sink 未就绪丢失边界**（假设 5）：不写测试（设计显式承认的 first-run 边界，非可断言行为——`lastResort` 是 stdlib 语义）；startup task 失败用例以 sink 已就绪前提断言三通道；
- **打点自身不破坏宿主**：全部新增打点路径的既有行为断言（re-raise 语义、返回值、异常类型）随域内既有测试原样跑绿覆盖。

## 手工验证步骤（若需）

批次①三卷交叉目验先例的对应项（结果记 verification.md）：

1. **loader 九场景抽验**：写入含非法 `[model_catalog]` 的 `aixcoding.toml` → 启动 TUI → `~/.chrys/aixcoding-logs/aixcoding.log` 出现中文 WARNING、stderr 同步输出；
2. **catalog 覆盖抽验**：mock server（`python -m aixcoding.mock`）+ 自建与下发同 id 模型 → 触发同步 → 主卷出现「已被后端版本覆盖」WARNING、detail 同文案；
3. **guard 重置抽验**：手工写坏 `hooks/hooks.yaml`（非法 YAML）→ 启动 → 主卷出现「已备份至 …pre-guard 并以安全护栏模板重置」WARNING、`.pre-guard` 文件存在；
4. **机器验证**：`uv run python aixcoding/tools/verify.py --smart --paths <全部改动文件>`；`uv run pytest aixcoding/tests -n0`；`uv run pytest tests/architecture -n0`；`uv run python aixcoding/tools/gen_customizations.py --strict`（0 error / 0 warning）；`uv run ruff check <改动文件>` + `uv run ruff format --check <改动文件>`。


## 实施回填（2026-11-20，PR #141 peer review C4）

实施期组织由"域内分散追加"收敛为**集中为主**（卷归属断言设施统一复用：`_spy`/`detail_spy`/参数化），实际落点与上文"测试文件组织"表的差异：

- 新建集中文件为 `aixcoding/tests/logging_coverage/test_coverage.py`（非 `diagnostics/test_logging_coverage.py`）——update 检查失败/静默/unbuildable/wrapper、skills、guard、config、startup、静态扫描、PII 哨兵全部在此；
- `test_client.py`/`test_runner.py`/`skills` 域内既有文件**未改动**（其打点由集中文件以 `transport=`/monkeypatch 注入覆盖）；
- 域内实际修订仅四文件：`test_flow.py`（CONFIRM/SKIP INFO+detail 双写）、`test_catalog_sync.py`（覆盖/清空/健康静默）、`test_config.py`（断言中文化）、`test_entry_wiring.py`（断言中文化）；
- 覆盖矩阵用例名以实际为准：`test_check_failure_branches_warn_main_volume`（五分支参数化）、`test_check_no_update_204_stays_silent`、`test_skills_team_filenotfound_silent` + `test_skills_team_permission_error_logged_detail`（C2 补）、`test_guard_unparsable_reset_warns_main_volume` 等；peer review 处置新增 `test_config_oserror_message_carries_no_path`（C1）。
