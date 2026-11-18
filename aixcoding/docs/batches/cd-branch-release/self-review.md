# 自评审记录：0.35.2 分支手动预发布

- 责任人：兰荣达
- 状态：已确认
- 确认日期：2026-11-17
- 确认意见：无

Codex GPT-6 Astra 独立评审了分支保护、构建 SHA、发布条件、制品归集及 action 权限，核对固定版本发布 action 支持新增输入。未发现阻断项。真实 Actions 发布验证尚未执行。

## 通用版本分支增量复审

Codex GPT-6 Astra 复审通过。独立运行九组分支匹配，核对签认范围、固定 SHA 及既有发布条件，未发现阻断项。

## 首次 CD 回归修复复审

Codex GPT-6 Astra 复核 wheel 校验和标签输出、正式发布与 PyPI 条件、定制标记及日志弹窗绑定，未发现阻断项。复审为只读检查，开发侧实跑结果见 [验证记录](verification.md#首次-cd-运行的回归修复)。

## Windows ARM64 依赖缓存增量评审

Codex GPT-6 Astra 核对了 setup-uv 缓存恢复与源码安装目录、vcpkg 文件缓存和原有离线与发布条件，未发现阻断项。已统一两处错误提示的 vcpkg 提交变量名。真实缓存命中和耗时待 Windows ARM64 runner 验证。

## 2026-11-17 测试打包与正式发布增量复审

- 评审工具为 Codex 独立子代理 cd_modes_independent_review，调用配置模型 gpt-6-astra；开发由本主会话执行。原签认字段保持。
- 两轮独立只读评审覆盖 R2/R3、上游 Tag/PyPI、公司 fork 的测试模式、产物命名与 checksum、Release 状态/API、备份和失败顺序。
- 已处置新增标题与并发配置的标记登记遗漏。针对外部并发创建 Tag 的风险，改为原子 POST git/refs，成功后 --verify-tag 发布。增量复审无 blocker。
- 复审实际重跑 /tmp/icode-cd-release-smoke.py，通过 dispatch、目标状态、制品及发布命令模拟；check_docs --closure 通过。实际 Python 3.14.8，保留项目请求 3.14.10 的警告。
- 持久化关键回归测试为建议项，本次用 /tmp 模拟留证。GitHub 发布权限和真实下游下载仍须联调。全局定制清单原生检查仍有 28 个旧工作树假阳性，未记为通过。

## 2026-11-18 正式发布二进制版本修复增量复核

Codex 独立上下文代理 cd_binary_version_review 核对当前 diff、签认 R2、resolve-build 的直接 job 依赖、R3 登记和持久化测试，未发现 blocker。代理独立执行六项串联回归与 check_docs --closure，均通过。调用指定 gpt-6.2-astra，代理只确认 GPT-6 family，无法自证精确模型变体，故本记录不凭该自报证明不同源身份。

开发侧 36 项定向测试通过。全局 strict 登记检查仍受旧工作树 28 项扫描错误影响，已在 verification 留存原始结果。真实 GitHub 发布仍待联调。保留原签认头部。
