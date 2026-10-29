# 测试方案：AI 流程闸门（ai-gates）

> 活文档：随时更新、不签认。纯文档批次——无产品代码、无自动化测试；验证方式为既有治理工具的机检 + 条文位置人工核对。

## 覆盖矩阵

| 验收标准（requirements.md） | 验证入口 | 类型 |
|---|---|---|
| DEVELOPMENT.md 含协作流程条款（判定单/停等）与豁免判定权条款 | verification.md #3 条文位置核对（§4.1/§4.2/§6） | 人工核对 |
| AGENTS.md 含协议摘要（判定单/豁免权/git 逐条授权/聊天认可≠实施信号） | verification.md #3 + AGENTS.md AIxCoding 段目视 | 人工核对 |
| git 逐条授权成为条文 | verification.md #3（§4.1 铁律四条化） | 人工核对 |
| check_docs 全绿 | `aixcoding/tools/check_docs.py` | 机检 |
| CUSTOMIZATIONS.md 幂等（AGENTS.md 改动后） | `aixcoding/tools/gen_customizations.py` 连跑两次 diff 稳定 | 机检 |

## 异常与降级路径

- 无（纯文档变更；治理工具异常属工具自身批次范畴）。
