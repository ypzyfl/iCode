# 测试方案：0.35.2 手册内容同步（user-manual-v0.35.2）

> 活文档：随时更新、不签认；其质量由双 AI 自审（SELF-REVIEW-HOWTO）与门禁本身保障。

## 测试范围与策略

纯文档内容批次，无代码改动——测试主体是**内容门禁链**（机械校验，全部已有工具化）：

1. 合并正确性：官方汇编/定稿与各自母本的 diff 断言（范围精确性）；
2. 内容质量：品牌/禁用词零豁免扫描、内锚校验、结构检查（manual-version-update SKILL §三清单）；
3. 双轨一致：六项审计逐章比对（F8 manual ↔ 桌面定稿，基准自动切换验证）；
4. 交付物：PDF 结构校验（页数/书签/链接注解/CHANNEL 变量）、wheel 捆绑哈希 + 新内容抽查；
5. 回归：手册契约测试（foundation/invoker/workflows/providers 四个 test_documentation）。

无新增测试文件——本批次不新增代码，不涉及上游 anchor，无行为锚定需求。

## 覆盖矩阵

| 验收标准（对应 requirements.md） | 测试入口 | 类型 |
|---|---|---|
| 官方汇编 diff = 封面 2 行 + 官方 6 处（8+/8-） | `git diff --no-index` 基线↔汇编 | 手工脚本断言 |
| manual 同步：本批次官方改动 10 文件 14 处（每处 count==1）+ zh CHANNEL 1 处 + en 追平类 22 整文件及混入 hunk（见 verification「en 侧追平清单」） | `.tmp_sync_manual.py` 逐处断言 + `git status --short -- aixcoding/manual/en` 清单核对 | 手工脚本断言 |
| docs/ 镜像追平归零 | `git diff v0.35.2 -- docs/zh-Hans docs/en docs/index.yaml` 输出为空 | 手工命令断言 |
| 品牌/禁用词 0、结构 0 | SKILL §三自检脚本（围栏感知） | 门禁 |
| 内锚 237 引用 0 失效、外链 0 | `check_links.py`（定稿 + manual 全量） | 门禁 |
| 六项审计全绿 + 基准自动切 0.35.2 | `audit_manual.py`（输出首行=基准路径） | 门禁 |
| check_docs / gen_customizations --strict | 两命令直跑 | 门禁 |
| PDF 137 页/书签 50 条/32 注解/CHANNEL | `add_bookmarks.py` 内置自校验 + pypdf 抽验脚本 | 门禁 + 手工 |
| 捆绑 64=64 MD5 + 0.35.2 新内容抽查 | `.tmp_bundle_check.py`（测试 venv 实装后跑） | 门禁 |
| 契约测试 26 passed | `pytest tests/foundation/test_documentation.py …` 四文件 | 契约 |

## 异常与降级路径

- 替换断言失败（count≠1）→ 立即终止不落盘（脚本设计为 fail-fast，先断言后写文件）；
- 官方汇编章体替换边界错误 → 与基线 diff 行数不吻合即暴露（实测首轮即抓出章体末尾空行
  缺失，修复后重生成）。

## 手工验证步骤（若需）

终端实测确认（用户侧）：

```
F8 手册搜索"下两级子目录"（0.35.2 独有关键词，一处命中即证明整批生效）
F8 搜索"6 行及以上"、"单击图片或引用标签可打开只读预览"、"搜索范围是复选框所选的全部会话"
```

结果记入 verification.md。
