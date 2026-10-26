# 验证记录：auth 迁入

> 活文档（不签认）。交付证据（R7）：实际执行的命令与输出摘要。每次验证追加一节，**不删旧记录**；
> 真实性由双 AI 自审与评审抽查保障。

环境配方（本地全量门禁标准四件套）：`set PYTHONPATH=` + `set PYTHONUTF8=1` +
`set UV_PYTHON=3.14.3` + 大写盘符启动；分支 `feat/auth_migration`；
R2/R3 gate 的 base = `3104004947f87c6f5e10cc56824f8c265adc193b`（merge-base origin/main_iCode）。

## 2026-10-26 探针式接线（design"实施流程约束"第 2 条）

命令：`uv run python aixcoding/tools/check_r2_diff.py --base 31040049...`

- 首跑：`unauthorized upstream change: clients.py / wire_client.py`，**批准池 5 不含本批两文件**——
  根因：design 的 R2 节标题自创后缀 `（R2 报批；...）`，`parse_table_section` 全等匹配不识别
  （模板节标题是机器接口）；改为标准形态 `（R2）`（语义零变化）后复跑：
  `check_r2_diff: OK`（approved_pool 5→7，upstream_changed=2 本批文件全在池内）。
- R10 处理：标题修正属签认后正文改动，负责人 2026-10-26 确认"延续原签认效力，继续"。
- 同根因第二处：`定制点登记预告` 节标题自创后缀 `（CUSTOMIZATIONS.md）` 同样不被
  `gen_customizations.py` 识别，同法修正（并入本轮汇报，见文末"实施后记"）。

## 2026-10-26 迁入实施（auth 9 文件 + 7 测试 + mock 联动）

命令：

```
uv run pytest aixcoding/tests/auth -m "not integration and not gc_calibration" -q
uv run ruff check aixcoding/ --no-fix
uv run ruff format --check aixcoding/
uv run python aixcoding/tools/check_import_boundaries.py
```

- pytest 首跑 `1 failed, 68 passed, 2 errors`：errors = 批量替换脚本笔误产生双重 `as`
  （`import ... as auth_session as auth_session` ×2，已修）；failed = mock 集成断言与
  PR #56 fixture 失配（`ehr 8769092→1234567`、`name 大熊猫→测试员`、
  `token_type AICoding→aixcoding-cli`），按 mock 批次先例"以实现为准"适配 8 处 mock 往返
  断言（测试自构数据行不动）；
- 修复后：**93 passed**；ruff check `All checks passed!`（测试文件头 noqa S101/S106[/S107]，
  ruff --fix 自动收敛未用码）；format 绿；import 边界 `OK`（1098→1099 文件）。
- 全仓 `CHRYS_AUTH_` 残留终验：7 文件全部符合 design"不回改"定性（ADR-0009/verification 历史/
  archaeology-report/auth design 映射表自身/`tests/foundation/util/test_env_templates.py` 无关
  样例 + 新甄别 `DIRECTORY.md:134`=规则描述自身，均不回改）；`aixcoding/mock/` 内残留 0。

## 2026-10-26 上游接线 + 行为锚定测试

命令：`uv run pytest aixcoding/tests/auth -q`（test_llm_token_wiring.py 新增 7 例）

- 首跑 `3 passed, 4 errors`：errors = 测试 fixture `store.store()` 少传 environment 参数
  （签名为 `store(environment, credential)`），修正后 **100 passed**（93 + 7 新增）；
- 通道 2（wire 级）：真实 openai SDK client + `httpx.MockTransport`，SDK 的
  default_headers × per-request extra_headers 合并真实发生，断言最终 wire 头
  `token == 登录 token`（胜过构造期静态 `token`）——SDK 合并行为未被 mock；
- `tests/service/llm`（上游相邻）：**2047 passed**。

## 2026-10-26 Smart Test（上游侧）

命令：`uv run python scripts/chrys_test.py --smart --paths src/chrys/service/llm/clients.py src/chrys/service/llm/wire_client.py`

- `1 failed, 16740 passed, 167 skipped`（11 分 03 秒）：唯一 failed =
  `tests/service/workflows/test_environment.py::test_prepare_probes_the_default_interpreter_and_fingerprints_it`
  ——与 LLM header/auth 零语义关联的解释器探测测试；**单文件复跑 56 passed 全绿**，判定满载
  偶发 flaky（与 test_gc_freeze_calibration 满载偶发同类，非本批引入）。

## 2026-10-26 ty 三平台（auth 首次进射程，design 预告的修复窗口）

命令：`uv run ty check --error-on-warning --python-platform {linux,win32,darwin} src/chrys`

- 首跑 19 处 error（三平台汇总）：**2 处真类型修复**——`environments.py` 两函数
  `environ: dict[str,str]|None` → `Mapping[str,str]|None`（`os._Environ` 非 dict 子类）、
  `storage.py` envelope 显式注解 `dict[str, object]`（dict 不变型）；
  **其余 16 错由 14 处行级 `# ty: ignore[...]` 覆盖**——`crypto.py` 7 行 9 错（ctypes 动态
  结构/WinDLL 跨平台解析；:158 一行含 pbData/cbData 两错共用一个 ignore；上游 18 处
  ty:ignore 同因先例）+ `types.py` 7 行 7 错（wire payload `object` 进 `int()/float()`，
  0.28 原样解析逻辑不顺手重构）；（评审 F-3 更正：初稿误记"17 处=9+7"）
- 修复后：linux `All checks passed!`（exit 0）、darwin `All checks passed!`（exit 0）、
  win32 **exit 0**（3 个 `unused-ignore-comment` warning：`WinDLL/get_last_error` 在
  win32 为合法符号、ignore 仅 linux/darwin 需要——平台相关 ignore 的固有两难，
  `--error-on-warning` 下 unused-ignore 不阻断，输出为日志噪音）。

## 2026-10-26 定制清单刷新（R8 机制）

命令：`uv run python aixcoding/tools/gen_customizations.py`

- 首跑 error：两个 marker `module login` 无登记行——marker module 词与登记落点
  （`src/chrys/aixcoding/auth/`）不匹配；marker 措辞 `AIxCoding login:` → `AIxCoding auth:`
  （module=auth，对齐 diagnostics/telemetry 的 module=特性名先例）后仍 error——即上述
  `定制点登记预告` 节标题第二处全等匹配坑，修正后：
- `gen_customizations: wrote aixcoding/docs/CUSTOMIZATIONS.md (7 custom point(s), 2 warning(s))`；
  2 warning 非阻断：上游接线点两登记行（`clients.py::_login_token()` 等）的 marker 归属由
  auth 包行吸收（module_matches 语义），"designed but not implemented" 措辞对本批是噪音，
  语义如实。`check_r3_markers: OK`（marker_checked=5）、`check_docs: OK`（9 ADR / 7 design）。

## 2026-10-26 全量门禁汇总（本批最终态）

- 定制侧全量：`uv run pytest aixcoding/tests -m "not integration and not gc_calibration" -q`
  → **263 passed, 2 skipped**（2 skip = catalog 消费者侧对拍，`chrys.service.profiles.models.catalog`
  0.31 不存在，skipif 自动生效，随 catalog 批次恢复）；
- 上游侧：`tests/service/llm` 2047 passed；Smart Test 16740 passed + 1 满载 flaky（单跑绿）；
- ruff check/format（两上游文件 + aixcoding 全域）：绿；
- ty 三平台：exit 0 ×3（win32 含 3 个非阻断 unused-ignore warning）；
- 四工具：check_r2_diff OK / check_r3_markers OK / check_import_boundaries OK / check_docs OK；
- CI 证据 = PR checks（GitHub 永久可查），按 DEVELOPMENT.md §7 不落盘本文件。

## 实施后记（同根因格式坑，两处）

本批踩中同一根因两次：**design 模板的节标题是机器接口（R2 表/登记表被 `check_r2_diff.py` /
`gen_customizations.py` 全等匹配），自创后缀导致机器读不到表**——第一次（R2 节）探针提前暴露，
第二次（登记预告节）清单刷新时暴露。两次修正均纯格式对齐、表内容零变化；第一次经负责人确认
"延续原签认效力"，第二次性质相同并入本记录（提交审批时一并可见）。改进项（独立小任务，不属
本批）：`check_docs.py` 增加 R2 节/登记节标题形态校验，防后续批次再踩。
