# 任务清单：TUI 自动更新流程（auto-update）

## 状态

requirements 五问全裁决、design 签认后实施完成（2026-11-11，A-D 全落地）；
首次人工冒烟引出的修订八～十三已全部落地并复验（wrapper 弃管道、下次提醒
语义、失败提示行、启动窗口两阶段等待、焦点内联高亮、去 30s 硬延迟）——
责任人确认弹框键盘与时机均正常（2026-11-11）。修订十四（R13 集中化，
2026-11-12 责任人裁决方案①）亦已落地：5 处散落 lint 豁免收为
`pyproject.toml` 单条目录级条目，R2 表新增一行、登记 C159；修订十五
（时钟注入）修掉本批新增用例的跨午夜失败。
定稿门禁（2026-11-12）：`verify.py --smart --paths` 因 `pyproject.toml`
升级为全量 `--full` —— 定制 697 passed 47 skipped、上游 38096 passed
143 skipped + 2 个已知 `tzset` 环境性 error（与本批无关）、architecture
守卫补跑 1251 passed 1 deselected；ruff/ty/`--strict` 111/152/0/
`check_docs --closure`/R2/R3 全绿（详见 verification.md「最终态 Smart
Test」）。手工冒烟 1-7 已做，Windows 实机（8）与真实内网联调待做。
**收尾待办：design 重签与 self-review 签认均已完成（责任人本人
2026-11-12 落盘，头部日期均为 11-12，`check_docs --closure` OK）→ PR**；
Windows 实机与内网联调可后置。

## 待办

- [x] 责任人签认 design.md（R10，2026-11-11）
- [x] 实施 A——service 档：`service/aixcoding/update/{client,state}.py` + config 扩展
- [x] 实施 B——app 档：`app/aixcoding/update/{flow,dialog,runner,commands}.py`
- [x] 实施 C——R2 接线：`app/tui/app.py` marker 行（C158）；i18n 取消（修订六）
- [x] 实施 D——测试五件（test-plan 覆盖矩阵，首轮 57 用例）
- [x] 首轮机器验证：auto_update 57 passed / aixcoding 全量 690 passed 47 skipped /
      `--strict` 110/151/0 / ruff / ty 三平台 / Smart Test（2 个环境性 error）
- [x] 首次人工冒烟 1-5 与修订八～十三的缺陷修复（逐节证据见 verification.md）
- [x] 手工冒烟 6（弹框键盘）、7（弹框时机）：责任人确认样式与时机正常
- [x] 最终态机器验证：auto_update 64 passed / ruff / format / ty（darwin）/
      `--strict` 111/152/0 / R2/R3 两门 OK / `check_docs.py` OK
- [x] 责任人裁定 R13 豁免（2026-11-12，方案①）并落地修订十四：删 3 个
      文件级 RUF001 + 2 个行内 S603，改 pyproject.toml 单条目录级条目；
      design §4 新增一行、§7 登记 C159、strict 预期 111/152/0
- [x] 责任人重签 design.md 头部签认字段（R2 清单变更＝修订六缩减 +
      修订十四新增 pyproject.toml，DEVELOPMENT §4.1；头部日期已由本人
      落盘为 2026-11-12）
- [ ] 责任人复核修订七～十四正文，以及几处与实施态不符的表述
      （§3.3 文案走 i18n、§2/§3.6 tier 表落点、§12 locales 回滚条目、
      §3.4 两平台"绝不使用管道"措辞与 Windows 实际形态）——
      属已签认正文的措辞复核，不影响本批提交，可在 PR 评审期处理
- [x] 责任人签认 self-review.md（R10，头部已落盘「已确认 / 2026-11-12」）
- [ ] Windows 实机冒烟（test-plan 冒烟 8，命令串断言已由 CI 覆盖）
- [ ] 真实内网全链路联调（后端就绪后，verification.md「待补」）
- [x] 最终态 Smart Test（最终 paths，2026-11-12 跑完）：定制 697 passed /
      上游 38096 passed + 2 个已知 `tzset` 环境性 error / architecture 补跑
      1251 passed；证据见 verification.md「最终态 Smart Test」
- [ ] PR：特性分支 → 网页建 PR → peer review（变更导览含「新增豁免清单」：
      C159 目录级豁免一条）
- [x] 责任人裁定 `test_is_today_uses_the_local_calendar_day`（核实系本批次
      新增）→ 修订十五固定当天中午，本地 00:26 CST 与三个时区均 64 passed

## 挂起与备忘

- D2 已定案（责任人方案，2026-11-11 三轮收敛）：双临时文件——①`update-failures`
  计数（wrapper 唯一写方＝失败追加一行，零删除）；②`update-skip-today` 当日跳过
  标记（flow 在计数 ≥3 时创建并删①；存在且今日 → 全天不做更新检查，仅通知；
  明日自动失效；用户删除②重启＝立即重试；计数不跨日）。细则 design §3.2/§3.4/§3.5；
- D4 已定案（2026-11-11，二轮修订**弃域名**）：更新指令与检测地址**同源**——检测
  URL＝base（`[update].base_url` > tier 默认，共享 environment 键、dev/prod 与
  auth/catalog 同主机）+ `api/v2/releases/check`；镜像根＝同一 base 的 origin +
  `/aixcoding/file/aixcoding`（prod 实效 `http://82.187.34.98/aixcoding/file/
  aixcoding`；`[update].base_url` 覆盖时两端整体移动）；catalog 同构，含 drift test；
- 后端就绪状态不可从开发环境验证（本机非生产环境，责任人 2026-11-11 澄清）；
  上线后真实链路验证随后端就绪补充 verification.md；
- `artifact.url` 解析保留不消费（design §3.1）——直装通道留后续批次；
- 会话 id 公共访问通道实施时核对（design §9 假设 2），不可得则 relaunch 降级不带 `-s`。
