# ADR-0009：fork 新增环境变量统一 AIXCODING 前缀

<!--
签认规则（R10）：责任人本人编辑本头部（状态→已确认、填日期，确认意见可选），AI 不得代填。
签认后修改正文需重新签认；被取代时由新 ADR 回指，本文状态行改为：被取代（被 ADR-00XX 取代）——括号内即后继编号（check_docs 按此格式校验）。
校验：uv run python aixcoding/tools/check_docs.py

命名与编号：NNNN-标题.md，取目录现有最大编号+1；编号被引用后不改号；
并行撞号罕见且必然被 git 同名冲突暴露，暴露早期重新编号即可。

ADR 判定 checklist（出 ADR 的门槛，任一"是"；粒度是决策不是功能）：
① 有被认真考虑但否决的备选方案
② 撤销代价高（依赖方向/目录落点/数据格式/对外契约）
③ 约束未来工作模式，后来者会问"为什么"
④ 依赖上游非公开接口或行为（另登记定制清单 anchor）
反面清单（不出）：模块内实现选择、唯一合理路径、纯文档修正。

自包含快照原则：决策节完整记录当时定的机制内容，写定不改；规范演进不回改本文——
重大规则变更出新 ADR，本文标"被取代"。指向规范的引用仅作导航注记
（"本文为决策时点快照；现行以 <规范条款> 为准"），不作为决策内容。

决策更新处理：决策实质变更 → 新建 ADR 取代（背景须引用旧 ADR 并说明"什么变了"），
旧 ADR 仅改头部状态、正文不动、不触发重签；原地修改仅限错别字/链接/背景补充等
非决策性修正。
-->

- 责任人：周彬
- 状态：已确认
- 确认日期：2026-10-25
- 确认意见：无特别意见

> 本文为决策时点快照；现行规则以 `DIRECTORY.md` §9 命名速查为准。

## 背景

fork 定制代码新增的环境变量存在两套前缀并存（0.28.0 全景考古）：

- `AIXCODING_*`（config.py，4 个）：注释自述"对齐 aixcoding 同名环境变量"——与
  aixcoding-continue 桌面端的跨产品契约；
- `CHRYS_AUTH_ENVIRONMENT` / `CHRYS_AUTH_SERVER_URL`（auth/environments.py）：
  注释自述"deliberately mirror the `CHRYS_*` convention of the host app"——跟随
  chrys 宿主进程命名空间；纯 fork 模块，上游不存在此变量，桌面端零消费（2026-10-25
  于 aixcoding-continue 全仓检索证实）；
- `CHRYS_MODEL_CATALOG_BASE_URL` / `CHRYS_MODEL_CATALOG_SYNC_INTERVAL`（catalog.py，
  上游文件定制点）：配置声明挂上游 foundation settings 体系
  （`chrys.foundation.config.settings`）。

分界逻辑（跨产品对齐 vs 宿主配置体系）存在于历史注释但**不显著**：`CHRYS_AUTH_*`
产生"伪上游变量"认知成本（上游代码/文档查无此变量，审阅者自然质疑归属——2026-10-25
mock design 审阅中负责人质询"为什么用 CHRYS 开头，是否为培养上游"即为此）。

## 决策

1. fork 定制代码**新增环境变量统一 `AIXCODING_` 前缀**；
2. **例外**：挂上游 foundation settings 声明体系的沿用 `CHRYS_`（宿主配置机制约束），
   并在所属特性 design 登记；
3. 存量 `CHRYS_AUTH_ENVIRONMENT` / `CHRYS_AUTH_SERVER_URL` 于 **auth 特性迁入时一次性
   更名** `AIXCODING_AUTH_ENVIRONMENT` / `AIXCODING_AUTH_SERVER_URL`（内部产品，无
   兼容期双前缀）。

## 理由

- 统一前缀消除"伪上游变量"误导，fork 定制变量的归属一眼可辨；
- 被否决备选及死因：
  - **保持 `CHRYS_AUTH_*`**（跟随宿主命名空间一致性）：认知成本永续，前缀分裂固化；
    "镜像宿主"理由对纯 fork 模块最弱（宿主一致性服务于进程内审美，不产生任何机制价值）；
  - **双前缀兼容期**（旧名 alias 过渡）：内部产品 + 桌面端零消费，双倍维护面属过度设计；
  - **`CHRYS_MODEL_CATALOG_*` 一并更名**：被否决——挂上游 settings 声明体系，改名侵入
    上游配置机制、违反最小改动原则（R1）。

## 后果

- 规范落地：DIRECTORY.md §9 命名速查新增该约定（含例外条款）；
- auth 特性迁入 design 须引用本 ADR 执行更名（模块 + 测试 + 文档联调配方 + mock README
  配方同步更新），mock 基建期间行为锚定不改名；
- 此后所有特性的新增环境变量命名受本决策约束（后来者问"为什么是 AIXCODING_"时指本文）；
- 首个决策出处：`docs/mock/design.md` 决策记录（一）——负责人 2026-10-25 结构化问答
  拍板后补正为正式 ADR。
