# 发布 Releases 操作指南

对应工作流：`.github/workflows/cd.yml`（Actions 页面名为 **CD**）。

## 原理

CD 工作流最后一个 job `release`（Publish release）的触发条件是：

```yaml
if: startsWith(github.ref, 'refs/tags/v') || startsWith(inputs.ref, 'v')
```

即只有两种情况会发布 Release：

1. push 了 `v*` 格式的 tag；
2. 手动 Run workflow 时，`ref` 输入填了 `v` 开头的 tag 名。

手动 Run workflow 时 `ref` 默认是 `main`，因此只会构建 artifacts，**不会发布 Release**——这是正常行为，不是故障。

## 方式一：推 tag 自动发布（标准流程，推荐）

```bash
# 1. 确认 pyproject.toml 中版本号已更新（版本真源），且 uv.lock 已随同提交
# 2. 完整 i18n pipeline 已跑（版本号写入 Project-Id-Version）

git tag v0.6.6          # 替换为实际版本，格式 vX.Y.Z
git push origin v0.6.6
```

push tag 后自动触发 CD，依次执行：

1. `ci` — 复用 ci.yml 做完整 PR 门禁，失败即中止；
2. `build-wheel` — 构建Python wheel；
3. `build-binaries` — 5 个平台的 PyApp 离线二进制（linux x86_64/aarch64、macos aarch64/x86_64、windows x86_64）；
4. `release` — 归集产物，打压缩包（Linux/macOS 用 tar.gz，Windows 用 zip），生成 `SHA256SUMS.txt`，通过 `softprops/action-gh-release` 创建 GitHub Release 并上传全部资产。

## 方式二：手动 Run workflow 发布

适用于 tag 已存在但需要重发、或补发某平台的场景。

1. GitHub → Actions → **CD** → **Run workflow**；
2. 参数填写：
   - **ref**：填已存在的 tag 名，如 `v0.6.6`（必须以 `v` 开头，否则只构建不发布）；
   - **platform**：`all`，或指定 `windows` / `macos` / `linux` 单平台重打；
3. 等待流水线跑完，Release 自动创建/更新。

### 注意事项

- **先打 tag 再触发**：若填的 tag 尚不存在，`action-gh-release` 会以该名字自动建 Release 并指向默认分支当前 commit，可能发布出错误的 commit。
- `ref` 填分支名（如 `main`）= 仅构建产物（dev 版本号 `vX.Y.Z-dev-<sha>`），artifacts 可在 run 页面下载，但不发布。
- `platform` 选单平台时同样会发布 Release（release job 不依赖 platform），只是资产只含该平台。

## 发布前检查清单

- [ ] `pyproject.toml` 版本已 bump，`uv.lock` 同 commit 提交（`uv sync --extra all` 后一起提交）；
- [ ] 完整 i18n pipeline 已执行（extract → update → translate → compile → check）；
- [ ] tag 指向的 commit 已合入主分支且 CI 全绿；
- [ ] 用户可见变更已同步更新 `docs/en/` 与 `docs/zh-Hans/`。

## 发布后验证

1. Releases 页面确认 tag、自动生成的 release notes、全部平台资产齐全；
2. 核对 `SHA256SUMS.txt` 与各文件哈希一致；
3. 下载一份对应平台的包，运行 `./aixcoding-cli --version` 验证版本号正确。
