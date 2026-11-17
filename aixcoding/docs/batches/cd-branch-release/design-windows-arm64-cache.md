# 补充设计：加速 Windows ARM64 离线打包

- 责任人：兰荣达
- 状态：已确认
- 确认日期： 2026-11-17
- 确认意见：无

## 拟批准范围

Windows ARM64 离线 job 当前在 setup-uv 恢复缓存后才切换到短路径，无法从短路径命中已恢复的源码构建结果。保留短路径，并在 setup-uv 执行前传入同一目录。缓存按依赖锁、CPython pin、构建约束、Windows 镜像和 vcpkg 提交区分。沿用 setup-uv 的缓存清理。

给 OpenSSL 启用 vcpkg 文件二进制缓存。使用仓库已有 SHA 固定版本的 actions/cache 持久化该目录，按 runner 镜像、vcpkg 提交与目标 triplet 区分。vcpkg 继续校验包 ABI；未命中时走既有源码构建。

## R2 清单

| 文件 | 范围 | 候选行数 |
| --- | --- | --- |
| `.github/workflows/cd.yml` | `build-binaries` 中的 Windows ARM64 缓存初始化、setup-uv 输入及 OpenSSL 源码准备 | +26/−5 |

依赖锁、离线包内容、目标矩阵、CI 和离线启动测试沿用现有规则。本次不改打包脚本或引入外部缓存服务。

## 验证与回退

本地核对 YAML、补丁与作业边界。审批后用同一版本分支执行一次冷构建和一次热构建，记录 setup-uv 和 vcpkg 命中、两个构建步骤和 ARM64 job 总耗时，并核对 ARM64 离线启动检查。缓存失效或未命中时依旧可以源码构建。回退工作流改动即可恢复原缓存行为。
