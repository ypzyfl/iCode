# 设计：0.35.2 分支手动预发布

- 责任人：兰荣达
- 状态：已确认
- 确认日期： 2026-11-17
- 确认意见：无

> 适用分支已由责任人补签扩展为通用版本分支，见 [补充设计](design-supplement.md)。下文保留首次签认的 0.35.2 范围。
>
> Windows ARM64 离线构建缓存经另行签认，见 [缓存补充设计](design-windows-arm64-cache.md)。
>
> 测试打包与正式发布入口经另行签认，见 [发布方式补充设计](design-refresh-release-assets.md)。

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
| cd-branch-release:run-title | `.github/workflows/cd.yml` | AIxCoding release modes: show the selected build and mode in the run title. | 1 | run-name | 低（操作识别） | 〔随点迁移〕随发布入口 |
| cd-branch-release:dispatch-concurrency | `.github/workflows/cd.yml` | AIxCoding release modes: allow only test runs to cancel a running build. | 1 | concurrency | 高（取消运行） | 〔随点迁移〕随发布入口 |
| cd-branch-release:resolve | `.github/workflows/cd.yml` | AIxCoding branch release: resolve and pin the build ref | 1 | resolve-build | 高（构建来源） | 〔机制退役〕分支发布不再依赖 CD |
| cd-branch-release:ci | `.github/workflows/cd.yml` | AIxCoding branch release: pass the resolved ref to CI | 1 | ci.with.build_ref | 高（验证来源） | 〔随点迁移〕随 resolve-build |
| cd-branch-release:wheel | `.github/workflows/cd.yml` | AIxCoding branch release: use the resolved ref for the wheel | 1 | build-wheel checkout | 高（制品来源） | 〔随点迁移〕随 resolve-build |
| cd-branch-release:wheel-release-version | `.github/workflows/cd.yml` | AIxCoding branch release: check the wheel before either release path | 1 | build-wheel version check | 高（发布版本） | 〔消费者退役〕停止分支预发布 |
| cd-branch-release:binaries | `.github/workflows/cd.yml` | AIxCoding branch release: use the resolved ref for binaries | 1 | build-binaries checkout | 高（制品来源） | 〔随点迁移〕随 resolve-build |
| cd-branch-release:windows-arm64-dependency-cache | `.github/workflows/cd.yml` | AIxCoding Windows ARM64 offline build: share the native dependency caches across runs. | 1 | build-binaries 中的 setup-uv 与 OpenSSL 构建准备 | 高（原生依赖缓存） | 〔机制退役〕Windows ARM64 不再从源码构建依赖 |
| cd-branch-release:publish | `.github/workflows/cd.yml` | AIxCoding release modes: publish only the selected release action. | 1 | release | 高（GitHub 发布） | 〔消费者退役〕停止从版本分支发布 |
| cd-branch-release:check-destination | `.github/workflows/cd.yml` | AIxCoding release modes: check the destination before building and publishing. | 1 | resolve-build、release 的目标核验 | 高（防止写错版本） | 〔随点迁移〕随 release |
