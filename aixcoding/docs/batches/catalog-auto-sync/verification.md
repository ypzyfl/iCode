# 验证记录：catalog-auto-sync

## 2026-11-11 实施验证（本地）

环境：Windows 11，大写盘符 `D:\` 启动，`PYTHONPATH` 清空、`PYTHONUTF8=1`（既有配方）。

### 文档阶段校验（草案 + P1-P4 评审修复后各一次）

```
uv run python aixcoding/tools/check_docs.py
→ check_docs: scanned 24 ADR(s), 38 design(s), 36 self-review(s) — OK

uv run python aixcoding/tools/gen_customizations.py --strict
→ check OK — 109 registration row(s) / 150 marker(s) / 0 warning(s)
```

### 实施后测试

```
uv run pytest aixcoding/tests/catalog aixcoding/tests/config -q
→ 110 passed in 72.34s
```

含新增：`test_auto_sync_gate.py`（三态矩阵 9 + 守卫/归属/resume/回归 7）、
`test_config.py` 追加 4 用例（未设置/真值×2/非法/逐字段降级）。

**过程发现与修复（在案）**：首跑 18 失败，根因 = 既有 catalog 测试经无参
`load_config()` 读到本机真实 `%APPDATA%\chrys\aixcoding.toml`（`environment="local"`），
新守卫按设计拦截——"测试读真实 HOME"的既有隐患被暴露。修复 = `catalog/conftest.py`
新增 autouse 夹具固定 prod 快照（全目录隔离真实配置），`test_the_tier_is_auths_tier`
恢复真实 loader（它经环境变量驱动），新测试桩补齐 `base_url` 字段。修复后 110 全绿。

### ruff

```
uv run ruff check <7 个改动 py 文件>          → All checks passed
uv run ruff format --check <7 个改动 py 文件>  → 7 files already formatted
（新测试文件先经 ruff format 修复一处折行）
```

### 实施后规范校验

check_docs OK；gen_customizations --strict OK（同上数字）。

### 未执行（责任人指示）

- **Smart Test 暂时跳过**（2026-11-11 用户指示）；已跑 catalog/config 两目录全量 + ruff。

### 手工 TUI 验证（2026-11-11，责任人执行）

独立 cmd 窗口起 mock server（:7777 监听确认）+ `AIXCODING_ENVIRONMENT=local` 起 TUI
（工作副本 iCode-fork_2，本机 TOML 为 local 且无 auto_sync，即默认关路径）。
责任人结论：**测试通过，没有问题**——LOCAL 默认不同步主路径（启动/登录无 catalog 请求、
模型目录保留、TUI 正常）手动确认。

### 实施轮评审②修复后复跑（2026-11-11）

`test_the_tier_is_auths_tier`：真实 loader 目录钉空 `tmp_path`，本机 TOML `base_url`
泄漏敏感性消除（GLM 评审②）。

```
uv run pytest aixcoding/tests/catalog aixcoding/tests/config -q  → 110 passed in 3.07s
uv run ruff check / format --check test_catalog_sync.py           → 过
```
