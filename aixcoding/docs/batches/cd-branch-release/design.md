# 设计：0.35.2 分支手动预发布

- 责任人：兰荣达
- 状态：已确认
- 确认日期： 2026-11-17
- 确认意见：无

## 方案概述

在 `ypzyfl/iCode` 的 CD 手动触发界面增加 `publish_branch_release`，缺省关闭。勾选且运行分支与 `ref` 一致时，允许从 `main_aixcoding_cli_0.35.2` 或 `main_aixcoding_cli_0.35.2_final` 创建 GitHub Pre-release。CI、wheel、二进制和发布标签指向同一次触发的 SHA。标签由 wheel 版本、运行 ID 和运行次数生成。上传本次构建的压缩包、wheel 和 SHA256SUMS.txt。正式标签和 PyPI 路径沿用原规则。

## 备选方案

只使用现有正式标签适用于单次发版。可重复的分支试包需要独立的标签和手动入口，复用现有 CD 可以使用同一套 CI、构建与产物收集逻辑。

## 上游改动清单（R2）

| 文件 | 修改范围 | 预估行数 |
| --- | --- | --- |
| `.github/workflows/cd.yml` | 增加手动发布输入及分支校验，解析固定构建 SHA，传给 CI 和两个构建 job，扩展 GitHub Release 的触发条件并设置预发布标签 | 候选 +49/−9，最终按 R3 补齐定制标记 |

## 验证与回退

验证允许的两个分支、关闭开关、无效分支与 ref 不一致、正式标签路径，以及 CI 和各产物统一引用触发 SHA。首次 GitHub 验证从所选分支手动触发，核对发布类型、资产和标签指向。任一构建 job 失败时无需进入发布 job。关闭开关可回到分支打包；恢复该项 CD 改动可移除入口。

## 定制点登记预告

| id | 落点 | marker 锚 | 预期计数 | anchor | risk | removal_condition |
| --- | --- | --- | --- | --- | --- | --- |
| cd-branch-release:dispatch | `.github/workflows/cd.yml` | AIxCoding branch release: opt-in dispatch input | 1 | workflow_dispatch.inputs | 高（发布入口） | 〔消费者退役〕停止分支预发布 |
| cd-branch-release:resolve | `.github/workflows/cd.yml` | AIxCoding branch release: resolve and pin the build ref | 1 | resolve-build | 高（构建来源） | 〔机制退役〕分支发布不再依赖 CD |
| cd-branch-release:ci | `.github/workflows/cd.yml` | AIxCoding branch release: pass the resolved ref to CI | 1 | ci.with.build_ref | 高（验证来源） | 〔随点迁移〕随 resolve-build |
| cd-branch-release:wheel | `.github/workflows/cd.yml` | AIxCoding branch release: use the resolved ref for the wheel | 1 | build-wheel checkout | 高（制品来源） | 〔随点迁移〕随 resolve-build |
| cd-branch-release:binaries | `.github/workflows/cd.yml` | AIxCoding branch release: use the resolved ref for binaries | 1 | build-binaries checkout | 高（制品来源） | 〔随点迁移〕随 resolve-build |
| cd-branch-release:publish | `.github/workflows/cd.yml` | AIxCoding branch release: publish opt-in builds as pre-releases | 1 | release | 高（GitHub 发布） | 〔消费者退役〕停止分支预发布 |
