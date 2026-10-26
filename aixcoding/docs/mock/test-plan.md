# 测试方案：mock 基建迁入

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与行为锚定测试本身保障。

## 测试范围与策略

- 层级：**契约测试**为主（mock 输出锚定后端 wire 契约）+ launcher 行为测试；
- 全部落 `aixcoding/tests/mock/`（显式运行，DIRECTORY.md §5），测试经 `create_server(port=0)`
  进程内起停（夹具随迁保持复制实现，不 import 上游 tests）；
- **避代理手法边界（有意并存，防"统一手法"无意破坏隔离）**：catalog 测试走 httpx +
  `direct_route` 夹具（conftest 设 `NO_PROXY='*'`）；update 测试走 urllib + 空
  `ProxyHandler`（自带隔离、注释明说"不用任何测试夹具"）——两种手法各自匹配其 HTTP
  客户端，`tests/mock/conftest.py` 的 `direct_route` 对 update 测试为无害冗余，维持现状
  不合并（2026-10-25 评审建议落字）；
- 行为锚定：catalog 契约测试 import 产品真实解析器 `chrys.service.profiles.models.catalog`
  的 `parse_catalog` / `ModelCatalogError`（真调上游符号断言行为；0.28→0.31 符号漂移
  由实施时重定位，见 design 假设 1）；
- update 契约测试保留 httpx async 形态（对齐产品端 `http.py` AsyncClient；上游主依赖零新增）。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口（文件::用例） | 类型 |
|---|---|---|
| auth 设备码申请 `result` 信封 | `test_auth_server.py`（新增最小集） | 契约 |
| auth 轮询 pending/authorized 交替与 `access_denied` | 同上 | 契约 |
| auth `user/info` `data` 信封 + 未知 token"HTTP 200 + code:400 无 success 键"怪癖 | 同上 | 契约 |
| update 四种模式（update/no_update/error/garbage）响应语义 | `test_update_server.py`（旧 418 行迁入） | 契约 |
| update debug 端点（config/reset/requests）与严格参数校验 | 同上 | 契约 |
| catalog 六种故障模式（ok/empty/invalid/error/slow/stale） | `test_model_catalog_server.py`（旧 250 行迁入） | 契约 |
| catalog dispatch payload 被产品解析器接受 | 同上（`parse_catalog` 真调） | 行为锚定 |
| catalog `empty`/`invalid` 拒绝路径（`ModelCatalogError`） | 同上（真调） | 行为锚定 |
| catalog 默认同端口内嵌 auth 路由（`--no-auth` 关闭） | 同上 | 契约 |
| launcher：`--list` / 默认组合起停 / 端口占用 fail-fast 报错 | `test_launcher.py`（launcher 逻辑单元）+ 手工冒烟 | 单元+手工 |
| 回滚无残留 | 手工（verification.md 记录） | 手工 |

## 异常与降级路径

- 端口占用（`OSError` EADDRINUSE）：明确报错定位服务 + 查占指引，**不静默换端口**
  （launcher 整体退出不起半套）——对应 requirements 验收项；
- `parse_catalog` 符号漂移：降级预案 = 暂去产品解析器对拍、保留 mock 行为断言，随
  auth 特性迁入补齐（design 风险节）；
- `slow` 故障模式：mock 侧锚定延迟行为本身；客户端 3s 超时降级由产品端测试覆盖
  （属 update_detection 特性，非本特性范围）。

## 手工验证步骤（若需）

1. `python -m aixcoding.mock` → 期望：起 model_catalog(:7777) + update(:7778)，打印
   地址清单与产品端 env 配方；
2. `curl -X POST http://127.0.0.1:7777/mock/control -d '{"mode":"error"}'` → 期望 200
   且 mode 生效；update `/debug/config` 同理；
3. 预占 7777（另起一个 server）再跑 launcher → 期望明确报错退出、无半开组合；
4. Ctrl+C → 期望两 server 干净退出无残留进程；
5. 结果记入 verification.md。
