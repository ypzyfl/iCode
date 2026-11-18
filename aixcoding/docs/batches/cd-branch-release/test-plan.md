# 测试方案：0.35.2 分支手动预发布

- 运行工作流内的分支解析脚本，覆盖当前与后续版本、可选 `_final` 后缀、关闭开关、非法分支名、ref 不匹配、标签、其他仓库和非法多行 ref。
- 核对 CI、wheel、二进制与发布 job 使用解析后的 SHA。用样本 wheel 执行资产收集脚本，核对派生标签、压缩文件和校验文件。
- 执行工作流 action 固定版本及 Python 版本门禁。首次真实运行时核对 Releases 页面、制品和标签指向。

## 测试打包与正式发布

- `aixcoding/tests/tools/test_cd_release_versions.py` 显式执行实际 YAML 的 Determine version、Determine binary and artifact names、Collect release assets。覆盖当前更新、后续版本新建、`_final` 分支、普通测试分支、ref 留空与上游 Tag；核对六平台文件名及 sha256sum。通过 fork verify 的全量定制测试运行，不依赖上游 Smart Test 选中该定制测试。

- 从实际 CD YAML 提取并执行解析及发布 Shell。核对默认测试打包跳过发布、版本分支与构建 SHA、非全平台拒绝、现有 Release 的状态、Tag 和草稿冲突。
- 用模拟制品收集六个平台安装包和 wheel，验证桌面端文件名、构建来源与哈希。删去 Windows ARM64 包验证发布前会失败。
- 模拟 GitHub CLI，核对更新时旧附件存档在覆盖前，`SHA256SUMS.txt` 最后上传。新建时先请求创建指向固定 SHA 的 Tag，成功后才发布 Release。若新建 Tag 后发布失败，保留该 Tag 和运行记录，人工核对后恢复发布。
- 在 GitHub 分别验证测试模式产出、附件覆盖及创建新版本。检查凭据权限、GitHub 写入结果和桌面端下游下载。先从含新 CD 定义的分支触发，即使测试的代码来源是历史 Tag。
