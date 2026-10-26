# 需求：mock 基建迁入

> 活文档：随时更新、不签认（git 留痕）；意图确认由 design 签认承载。

## 背景与问题

阶段三首个迁入项：auth / update / model_catalog 三特性的迁入验收均以各自 mock 就位为
前提（依赖驱动）；旧分支手动 TUI 联调需分别记住并启动多个 mock server（auth :7777 /
update :7778，将来 telemetry :4321），痛点真实。

## 目标与非目标

- 目标：三服务复制迁入 `aixcoding/mock/`（零上游改动）；契约测试落
  `aixcoding/tests/mock/`；包根组合启动器一键起基础组合。
- 非目标：M4（telemetry-mock）随 telemetry 殿后；不改任何产品端代码与 env 名
  （行为锚定）；不合并单 server（已否决，见 design）。

## 用户场景

1. 手动 TUI 联调：`python -m aixcoding.mock` 一键起 model_catalog(:7777 含内嵌 auth) +
   update(:7778)，打印地址与产品端配置配方；
2. 契约回归：CI（aixcoding-tests.yml）显式运行 `aixcoding/tests/mock/`，锚定三 mock
   的 wire 复刻不漂移；
3. 单服务调试：直跑 `python aixcoding/mock/<name>/server.py` 或 `python -m` 独立起服务。

## 验收标准

- [ ] `aixcoding/mock/` 三子包 + 包根（`__init__.py`/`__main__.py`/README）结构符合
      DIRECTORY.md §6（含 launcher 编排层登记）；
- [ ] 三 mock 各有契约测试（auth 为最小集）且全绿：`uv run pytest aixcoding/tests`；
- [ ] ruff check / format `aixcoding/` 通过；`check_import_boundaries.py` 通过；
- [ ] launcher：`--list` 列清单；默认组合起停正常；端口被占 fail-fast 明确报错
      （不静默换端口）、Ctrl+C 干净退出；
- [ ] CI（aixcoding-tests.yml）全绿；
- [ ] 回滚验证路径成立：删 `aixcoding/mock/` 与 `aixcoding/tests/mock/` 无残留。

## 开放问题

- 0.31.0 `parse_catalog` 符号漂移（design 假设 1）：实施时重定位，若暂不可用按 design
  降级预案处理，随 auth 特性迁入补齐。
