#!/usr/bin/env bash
#
# AIxCoding-CLI TUI 安装器（内网友好）
#
# 在线安装（先下载脚本，下载失败时不会启动安装）:
#   curl -fsSL -o install.sh http://82.187.34.98/aixcoding/file/aixcoding/install.sh && bash install.sh
#
# 在线模式从制品镜像（ICODE_BASE_URL）下载；离线模式（--from）直接安装本地包。
# 安装动作复用包内可执行文件的 `install` 命令，再创建 aixcoding 启动命令。
#
# 镜像侧文件（ICODE_BASE_URL 指向 TUI 根目录）:
#   install.sh                                          本安装器（即本文件）
#   channels/cli/prod.txt、channels/cli/test.txt                各环境当前指向的完整版本号
#   releases/cli/<完整版本>/aixcoding-cli-<平台>-v<版本>-offline.tar.gz|.zip
#
# 发版时先上传 releases/cli/<完整版本>/，最后更新对应的 channels/cli/*.txt。
#
set -Eeuo pipefail

# ===== 配置区（也可用环境变量覆盖） =====
ICODE_BASE_URL="${ICODE_BASE_URL:-http://82.187.34.98/aixcoding/file/aixcoding}"
CHANNEL="${ICODE_CHANNEL:-prod}"

# ======================================================================

# ===== 全局状态 =====
VERSION=""
FROM=""
EXPECTED_SHA256=""
OS=""
MACHINE=""
PLATFORM=""
CHANNEL_LABEL=""
CHANNEL_FILE=""
ARCHIVE=""
ARCHIVE_NAME=""
WORK_DIR=""
EXTRACT_DIR=""
BINARY_PATH=""
BINARY_NAME=""
RC_FILE=""
STAGE="解析参数"

# ===== 基础工具 =====
die()  { printf '错误: %s\n' "$*" >&2; exit 1; }
info() { printf '==> %s\n' "$*"; }
warn() { printf '警告: %s\n' "$*" >&2; }

unexpected_error() {
  local code=$1 line=$2
  printf '错误: %s 阶段意外失败（脚本第 %s 行，退出码 %s）\n' "$STAGE" "$line" "$code" >&2
}

trap 'unexpected_error "$?" "$LINENO"' ERR

need() { command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1，请先安装"; }

sha256_of() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | cut -d' ' -f1
  else
    need sha256sum
    sha256sum "$1" | cut -d' ' -f1
  fi
}

# fetch <url> <输出文件> [--show-progress]
# 统一的下载入口；缺文件通常返回 22（HTTP）或 78（FTP）。
fetch() {
  local url=$1 out=$2 mode=${3:-}
  local args=(--fail --location --retry 3 --connect-timeout 15)
  if [ "$mode" = "--show-progress" ]; then
    args+=(--progress-bar)
  else
    args+=(-sS)
  fi
  case "$url" in
    ftp://*|ftps://*) args+=(--netrc-optional) ;;
  esac
  curl "${args[@]}" ${CURL_EXTRA:-} -o "$out" "$url"
}

usage() {
  cat <<EOF
AIxCoding-CLI TUI 安装器（macOS / Linux）

安装后的启动命令: aixcoding

在线安装（默认生产包，先确认脚本下载成功）:
  curl -fsSL -o install.sh ${ICODE_BASE_URL}/install.sh && bash install.sh

用法:
  bash install.sh                            在线安装生产包当前版本
  bash install.sh --channel test             在线安装测试包当前版本
  bash install.sh --version v0.28.0          在线安装指定版本
  bash install.sh --from <包路径>            离线安装本地包（tar.gz / zip）

选项（等号形式同样支持，如 --version=v0.28.0）:
  --channel <prod|test>  选择生产包或测试包（默认 prod）
  --sha256 <digest>   可选：用指定的 SHA-256 摘要校验安装包
  -h, --help          显示本帮助

环境变量:
  ICODE_BASE_URL      TUI 镜像根地址（当前: ${ICODE_BASE_URL}）
  ICODE_CHANNEL       默认环境，prod 或 test（当前: ${CHANNEL}）
  CURL_EXTRA          追加给 curl 的额外参数（如代理）
EOF
}

# ===== 阶段函数 =====
parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --version)    [ $# -ge 2 ] && [ -n "$2" ] || die "--version 需要非空版本号"; VERSION=$2; shift 2 ;;
      --version=*)  VERSION=${1#--version=}; [ -n "$VERSION" ] || die "--version 需要非空版本号"; shift ;;
      --channel)    [ $# -ge 2 ] && [ -n "$2" ] || die "--channel 需要 prod 或 test"; CHANNEL=$2; shift 2 ;;
      --channel=*)  CHANNEL=${1#--channel=}; [ -n "$CHANNEL" ] || die "--channel 需要 prod 或 test"; shift ;;
      --from)       [ $# -ge 2 ] && [ -n "$2" ] || die "--from 需要非空包路径"; FROM=$2; shift 2 ;;
      --from=*)     FROM=${1#--from=}; [ -n "$FROM" ] || die "--from 需要非空包路径"; shift ;;
      --sha256)     [ $# -ge 2 ] && [ -n "$2" ] || die "--sha256 需要非空摘要"; EXPECTED_SHA256=$2; shift 2 ;;
      --sha256=*)   EXPECTED_SHA256=${1#--sha256=}; [ -n "$EXPECTED_SHA256" ] || die "--sha256 需要非空摘要"; shift ;;
      -h|--help)    usage; exit 0 ;;
      *)            usage >&2; die "未知参数: $1" ;;
    esac
  done
  [ -z "$FROM" ] || [ -z "$VERSION" ] || die "--from 与 --version 不能同时使用"
  if [ -n "$EXPECTED_SHA256" ]; then
    [[ "$EXPECTED_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || die "--sha256 需要 64 位十六进制摘要"
  fi
}

resolve_channel() {
  case "$CHANNEL" in
    prod|production|生产包)
      CHANNEL_LABEL=生产包
      CHANNEL=prod
      ;;
    test|测试包)
      CHANNEL_LABEL=测试包
      CHANNEL=test
      ;;
    *) die "无效环境: ${CHANNEL}（只能是 prod 或 test）" ;;
  esac
  CHANNEL_FILE="${ICODE_BASE_URL%/}/channels/cli/${CHANNEL}.txt"
}

detect_platform() {
  OS=$(uname -s)
  MACHINE=$(uname -m)
  case "${OS}:${MACHINE}" in
    Darwin:arm64)              PLATFORM=macos-aarch64 ;;
    Darwin:x86_64)             PLATFORM=macos-x86_64 ;;
    Linux:x86_64)              PLATFORM=linux-x86_64 ;;
    Linux:aarch64|Linux:arm64) PLATFORM=linux-aarch64 ;;
    MINGW*:*|MSYS*:*|CYGWIN*:*)
      die "检测到 Windows。请下载 aixcoding-cli-windows-x86_64-v<版本>-offline.zip，解压后在 PowerShell 运行: .\\aixcoding-cli.exe install" ;;
    *) die "不支持的系统/架构: ${OS}:${MACHINE}" ;;
  esac
}

check_glibc() {
  [ "$OS" = Linux ] || return 0
  need ldd
  need awk
  local ldd_output ldd_first_line last_field glibc_version glibc_floor
  if ldd_output=$(ldd --version 2>&1); then
    :
  else
    case "$ldd_output" in
      *musl*) die "检测到 musl (Alpine)。iCode 不支持 musl，请使用 glibc 发行版" ;;
    esac
    die "无法读取 libc 版本: ${ldd_output:-ldd 未返回信息}"
  fi
  ldd_first_line=${ldd_output%%$'\n'*}
  case "$ldd_output" in
    *musl*) die "检测到 musl (Alpine)。iCode 不支持 musl，请使用 glibc 发行版" ;;
  esac
  # 版本号通常在首行最后一个字段，如 "ldd (Ubuntu GLIBC 2.35-0ubuntu3.1) 2.35"；
  # 若末字段不是版本号，再从整行取最后一个形如 X.Y[.Z] 的片段兜底。
  last_field=$(printf '%s\n' "$ldd_first_line" | awk '{print $NF}')
  glibc_version=$(printf '%s' "$last_field" | grep -oE '^[0-9]+(\.[0-9]+)+' || true)
  if [ -z "$glibc_version" ]; then
    glibc_version=$(printf '%s' "$ldd_first_line" | grep -oE '[0-9]+(\.[0-9]+)+' | tail -n 1 || true)
  fi
  if [ -z "$glibc_version" ]; then
    warn "无法解析 glibc 版本，跳过下限检查"
    return 0
  fi
  if [ "$PLATFORM" = linux-aarch64 ]; then
    glibc_floor=2.18
  else
    glibc_floor=2.17
  fi
  # 按点分段数值比较（浮点比较会把 glibc 2.9 误判为 >= 2.17）
  if ! awk -v a="$glibc_version" -v b="$glibc_floor" 'BEGIN {
    na = split(a, x, "."); nb = split(b, y, ".")
    for (i = 1; i <= na || i <= nb; i++) {
      xi = (i <= na) ? x[i] + 0 : 0
      yi = (i <= nb) ? y[i] + 0 : 0
      if (xi != yi) exit (xi < yi) ? 1 : 0
    }
  }'; then
    die "glibc ${glibc_version} 低于 ${PLATFORM} 的最低要求 ${glibc_floor}"
  fi
}

obtain_archive() {
  if [ -n "$FROM" ]; then
    # 离线模式：本地包
    [ -f "$FROM" ] || die "包不存在: $FROM"
    case "$FROM" in
      *.tar.gz|*.tgz|*.zip) : ;;
      *) die "不支持的安装包格式: ${FROM}（需要 .tar.gz、.tgz 或 .zip）" ;;
    esac
    ARCHIVE=$FROM
    ARCHIVE_NAME=$(basename -- "$FROM")
    info "使用本地安装包: ${ARCHIVE}"
    return 0
  fi

  # 在线模式：从镜像下载
  need curl
  VERSION="${VERSION#v}"
  if [ -z "$VERSION" ]; then
    info "获取${CHANNEL_LABEL}当前版本号（${CHANNEL_FILE}）"
    local rc=0
    fetch "$CHANNEL_FILE" "${WORK_DIR}/channel.txt" || rc=$?
    [ "$rc" -eq 0 ] || die "无法获取 channels/cli/${CHANNEL}.txt（curl exit ${rc}）。请检查镜像地址与网络；或用 --version 指定版本；或用 --from 离线安装"
    VERSION=$(sed -E 's/^[[:space:]]*[vV][[:space:]]*//; s/[[:space:]]*$//' "${WORK_DIR}/channel.txt" | tr -d '\r')
    [ -n "$VERSION" ] || die "channels/cli/${CHANNEL}.txt 内容为空（应为一行完整版本号，如 0.28.0）"
  fi
  [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([._-][[:alnum:]._-]+)?$ ]] || die "版本号格式无效: ${VERSION}（检查 channels/cli/${CHANNEL}.txt 或 --version）"

  # 在线下载：优先当前包名，并兼容已发布的 icode-* 安装包。
  local asset="" rc=0
  for candidate in \
    "aixcoding-cli-${PLATFORM}-v${VERSION}-offline.tar.gz" \
    "aixcoding-cli-${PLATFORM}-v${VERSION}-offline.zip" \
    "icode-${PLATFORM}-v${VERSION}-offline.tar.gz" \
    "icode-${PLATFORM}-v${VERSION}-offline.zip"; do
    info "下载 ${ICODE_BASE_URL%/}/releases/cli/${VERSION}/${candidate}"
    rc=0
    fetch "${ICODE_BASE_URL%/}/releases/cli/${VERSION}/${candidate}" "${WORK_DIR}/${candidate}" --show-progress || rc=$?
    if [ "$rc" -eq 0 ]; then
      asset=$candidate
      break
    fi
    # 缺文件时再尝试另一种包名或格式；网络和认证错误直接报出。
    [ "$rc" -eq 22 ] || [ "$rc" -eq 78 ] || break
  done
  if [ -z "$asset" ]; then
    if [ "$rc" -eq 22 ] || [ "$rc" -eq 78 ]; then
      die "下载失败（远端文件不存在）: 检查 releases/cli/${VERSION}/ 中 ${PLATFORM} 平台的安装包，以及 channels/cli/${CHANNEL}.txt 指向的版本；也可用 --from 安装本地包"
    fi
    die "下载失败（curl exit ${rc}）。检查网络/代理（可用 CURL_EXTRA 传参），或改用 --from 离线安装"
  fi
  ARCHIVE="${WORK_DIR}/${asset}"
  ARCHIVE_NAME=$asset
}

verify_archive() {
  if [ -z "$EXPECTED_SHA256" ]; then
    return 0
  fi
  info "校验 sha256（${ARCHIVE_NAME}）"
  local actual
  actual=$(sha256_of "$ARCHIVE")
  if [ "$actual" != "$(printf '%s' "$EXPECTED_SHA256" | tr '[:upper:]' '[:lower:]')" ]; then
    die "sha256 不匹配！期望 ${EXPECTED_SHA256}，实际 ${actual}，拒绝安装"
  fi
  info "校验通过"
}

extract_archive() {
  info "解压 ${ARCHIVE_NAME}"
  EXTRACT_DIR="${WORK_DIR}/extract"
  mkdir -p "$EXTRACT_DIR"
  case "$ARCHIVE_NAME" in
    *.zip)
      need unzip
      unzip -q "$ARCHIVE" -d "$EXTRACT_DIR" || die "ZIP 解压失败: ${ARCHIVE_NAME}（文件可能损坏或不是 ZIP）"
      ;;
    *)
      need tar
      tar -xzf "$ARCHIVE" -C "$EXTRACT_DIR" || die "tar.gz 解压失败: ${ARCHIVE_NAME}（文件可能损坏或格式不符）"
      ;;
  esac
  if [ -f "${EXTRACT_DIR}/aixcoding-cli" ]; then
    BINARY_NAME=aixcoding-cli
  elif [ -f "${EXTRACT_DIR}/icode" ]; then
    BINARY_NAME=icode
  elif [ -f "${EXTRACT_DIR}/aixcoding-cli.exe" ] || [ -f "${EXTRACT_DIR}/icode.exe" ]; then
    die "这是 Windows 安装包（内含 .exe 可执行文件）。请在 Windows 上解压后运行对应的 .exe install"
  else
    die "包内未找到根目录下的 aixcoding-cli 或 icode 可执行文件；请核对安装包内容和平台"
  fi
  BINARY_PATH="${EXTRACT_DIR}/${BINARY_NAME}"
  chmod +x "$BINARY_PATH"
  info "包内可执行文件: ${BINARY_NAME}"
  # macOS：清除从浏览器下载带来的隔离标记（curl 下载不会产生）
  if [ "$OS" = Darwin ]; then
    xattr -d com.apple.quarantine "$BINARY_PATH" 2>/dev/null || true
  fi
}

show_installed_version() {
  local installed=""
  if [ -x "${HOME}/.local/bin/aixcoding" ]; then
    installed=$("${HOME}/.local/bin/aixcoding" --version 2>/dev/null || true)
  elif command -v aixcoding-cli >/dev/null 2>&1; then
    installed=$(aixcoding-cli --version 2>/dev/null || true)
  elif command -v chrys >/dev/null 2>&1; then
    installed=$(chrys --version 2>/dev/null || true)
  fi
  [ -z "$installed" ] || info "当前已安装版本: ${installed}（本次将覆盖升级）"
}

smoke_test() {
  info "运行包内二进制自检（首次运行会解包内嵌 Python 运行时，可能耗时数秒）"
  local new_version rc
  if new_version=$("$BINARY_PATH" --version 2>&1); then
    [ -n "$new_version" ] || die "包内 ./${BINARY_NAME} --version 没有输出，拒绝安装"
  else
    rc=$?
    die "包内 ./${BINARY_NAME} --version 失败（退出码 ${rc}）：${new_version:0:1200}
请确认包内是 ${PLATFORM} 可执行文件，且系统满足运行要求"
  fi
  info "包版本: ${new_version}"
}

run_official_install() {
  info "执行官方安装命令: ./${BINARY_NAME} install"
  local rc
  if "$BINARY_PATH" install; then
    return 0
  else
    rc=$?
    die "./${BINARY_NAME} install 失败（退出码 ${rc}）；请查看上方安装器输出"
  fi
}

create_launch_command() {
  local install_dir="${HOME}/.local/bin"
  local binary="${install_dir}/chrys"
  local command_path="${install_dir}/aixcoding"
  [ -f "$binary" ] || die "安装命令结束后未找到 ${binary}，无法创建 aixcoding 启动命令"
  if [ -e "$command_path" ] || [ -L "$command_path" ]; then
    if [ "$command_path" -ef "$binary" ]; then
      info "启动命令已存在: ${command_path}"
      return 0
    fi
    die "${command_path} 已存在且不是本次安装的程序，请检查该文件后再安装"
  fi
  ln -s chrys "$command_path" || die "创建 ${command_path} 失败，请检查 ~/.local/bin 权限"
  info "已创建启动命令: ${command_path}"
}

persist_path() {
  # 包内可执行文件的 `install` 只打印修复指引不落盘；这里自动把 ~/.local/bin 幂等写入
  # 当前用户 shell 的 rc 文件，让新开终端开箱即用。
  local shell_name added=false
  shell_name=$(basename "${SHELL:-/bin/bash}")
  case "$shell_name" in
    zsh) RC_FILE="$HOME/.zshrc" ;;
    *)   RC_FILE="$HOME/.bashrc" ;;
  esac
  if ! grep -q '\.local/bin' "$RC_FILE" 2>/dev/null; then
    {
      printf '\n# Added by iCode installer\n'
      printf 'export PATH="$HOME/.local/bin:$PATH"\n'
    } >> "$RC_FILE"
    added=true
  fi
  # bash 登录 shell 兜底：存在 .bash_profile 却不加载 .bashrc 时补一行（覆盖 ssh 登录场景）
  if [ "$shell_name" != zsh ] && [ -f "$HOME/.bash_profile" ] && ! grep -q 'bashrc' "$HOME/.bash_profile" 2>/dev/null; then
    printf '[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"\n' >> "$HOME/.bash_profile"
    added=true
  fi
  if [ "$added" = true ]; then
    info "已将 ~/.local/bin 写入 ${RC_FILE}（新开终端自动生效，无需手动 export）"
  else
    info "PATH 配置已存在于 ${RC_FILE}，无需修改"
  fi
}

print_finish() {
  case ":${PATH}:" in
    *":${HOME}/.local/bin:"*) : ;;
    *)
      warn "当前这个终端尚未生效，执行以下命令立即可用（或直接重开终端）:"
      warn "  source ${RC_FILE}"
      ;;
  esac
  info "安装完成！新开终端后在任意目录运行: aixcoding"
}

# ===== 主流程 =====
main() {
  STAGE="解析参数"
  parse_args "$@"
  STAGE="选择环境"
  resolve_channel
  [ -n "${HOME:-}" ] || die "HOME 未设置，无法确定当前用户的安装目录"
  STAGE="检测平台"
  detect_platform
  STAGE="检查 libc"
  check_glibc
  STAGE="创建临时目录"
  WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/icode-install.XXXXXX") || die "无法创建临时目录，请检查 TMPDIR 的空间和权限"
  trap 'rm -rf "$WORK_DIR"' EXIT

  STAGE="获取安装包"
  obtain_archive
  STAGE="校验安装包"
  verify_archive
  STAGE="解压安装包"
  extract_archive
  STAGE="检测已安装版本"
  show_installed_version
  STAGE="运行二进制自检"
  smoke_test
  STAGE="执行安装"
  run_official_install
  STAGE="创建启动命令"
  create_launch_command
  STAGE="配置 PATH"
  persist_path
  STAGE="完成安装"
  print_finish
}

main "$@"
