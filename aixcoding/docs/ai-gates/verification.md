# 验证证据：AI 流程闸门（ai-gates）

> 活文档：命令 + 输出摘要（R7 落盘形态，追加不删旧）。

## 2026-10-29 实施验证

环境：Windows，venv Python 直跑（`uv run` 因 icode.exe 被占用进程锁定而 sync 失败，脚本均纯 stdlib，与运行方式无关）。

| # | 命令 | 结果摘要 |
|---|---|---|
| 1 | `.venv\Scripts\python.exe aixcoding/tools/check_docs.py`（design 签认后） | 首跑 1 error（design 保留空 R11 节触发审批字段校验——模板约定无依赖删节）→ 删除该节后 **OK**（12 ADR / 10 design / 7 self-review，含 ai-gates/design 已确认与 ADR-0012 草案格式） |
| 2 | `.venv\Scripts\python.exe aixcoding/tools/gen_customizations.py`（AGENTS.md 改动后，连跑两次） | 29 custom points；首跑 warning 2（ai-gates 登记行落点写法与 C001 module 匹配不上）→ 登记行落点改为归属模块路径 `aixcoding/docs/standards` 后 **warning 1**（仅剩 auth 既有遗留，非本批引入）；`git diff CUSTOMIZATIONS.md` 连跑两次稳定为 1 insertion + 1 deletion（C001 行 anchor/来源列追加 ai-gates 登记——预期产物，随提交纳入） |
| 3 | 实施核对 | DEVELOPMENT.md 三处（§4.1 铁律四条化 + §4.2 判定单协议与免判定清单 + §6 豁免判定权归责任人）；AGENTS.md AIxCoding 段 +12 行英文协议摘要（marker 行 `AGENTS.md:5` 文本不变）；ADR-0012 草案落 `standards/adr/`（全局池，编号 0011+1） |

R2 批准对应：AGENTS.md 一项（design 签认 2026-10-29，确认意见"先实施，实践过程中有问题再研究"）；`aixcoding-tests.yml` 随探测否决不再改动。
