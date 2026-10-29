# 需求：tui 迁入（登录对话框 + 会话徽标 + /login、/logout 命令）

## 目标与非目标

- 目标：把 0.28 定制版的 login 特性 UI 层迁入 0.31 基线——登录对话框（LoginDialog）、
  头部会话徽标（login indicator）、`/login` `/logout` 命令、启动静默凭据校验（silent check）
  四件套；全部领域逻辑落位 `src/chrys/app/aixcoding/tui/`（ADR-0011 app 档）。
- 非目标：不迁 catalog 联动实调（`start_catalog_sync`/`stop_catalog_sync` 以注释占位留给
  catalog 批次——决策 D3）；不迁 update badge（update 批次）；不改 auth 内核
  （PR #60/#64 已就位）；不引入英文文案资产（ADR-0010 中文单语）。

## 用户场景

1. 银行内网用户敲 `/login`：弹出设备码对话框，浏览器自动打开预填验证页，授权后 toast
   "已登录：<名>"，header 出现绿色 ● 徽标。
2. 启动 iCode（已有存储凭据）：静默校验，徽标直接显示已登录；离线启动回退显示工号；
   凭据被服务端拒绝时自清理并翻转为未登录灰态。
3. 桌面端代登录（delegated credential）：`/login` `/logout` 均提示"由桌面端管理"，
   不弹对话框、不清凭据。
4. diff 屏：header 无 login 徽标（`show_login_badge=False`）。

## 验收标准

- [x] `aixcoding/tests/tui/` 25 用例绿（对话框 3、wiring 7、indicator 9、徽标 2、命令 4）。
- [x] Smart Test 全量绿（32357 passed；唯一 1 失败为在案的 gc_freeze_calibration 满载
      flaky，单独复跑绿）+ architecture 1237 绿（test_layering 零豁免）。
- [x] R2 门禁：`check_r2_diff --base main_aixcoding_cli` 全部 approved（16 文件 +
      5 项历史批准，零 unauthorized）。
- [x] i18n 三方一致：`i18n.py check` OK；pot 4 key / po msgstr=fallback 中文复制 /
      oracle 登记 +4（2401→2405）实测落地。
- [x] ty check（win32）绿；ruff check + format 绿。
- [x] 全部上游改动带 `# AIxCoding tui:` 标记注释；CUSTOMIZATIONS.md 重新生成（28 定制点）。
