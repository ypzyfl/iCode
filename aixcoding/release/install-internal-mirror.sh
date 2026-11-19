#!/usr/bin/env bash
# Install or upgrade AIxCoding from the internal release mirror (macOS and Linux).
#
# The mirror layout is documented in aixcoding/docs/batches/internal-installer/publishing.md.
# The package's own `install` command creates `chrys` and its `aixcoding-cli` alias.

set -Eeuo pipefail

DEFAULT_BASE_URL="http://aicoding.s.bocsys.cn/aixcoding/file/aixcoding"
BASE_URL="${AIXCODING_BASE_URL:-${ICODE_BASE_URL:-$DEFAULT_BASE_URL}}"
CHANNEL="${AIXCODING_CHANNEL:-${ICODE_CHANNEL:-prod}}"

VERSION=""
FORCE=false
INSTALLED_VERSION=""
LOG_FILE=""
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
BIN_DIR=""
EXTERNAL_COMMAND=""
OWNED_ALIASES=" "
RC_FILE=""
STAGE="解析参数"

die() {
  printf '错误: %s\n' "$*" >&2
  if [ -n "$LOG_FILE" ]; then
    printf 'Stage: %s; error: %s\n' "$STAGE" "$*" >>"$LOG_FILE"
    printf '详细日志: %s\n' "$LOG_FILE" >&2
  fi
  exit 1
}
info() { printf '==> %s\n' "$*"; }
warn() { printf '警告: %s\n' "$*" >&2; }

unexpected_error() {
  local code=$1 line=$2
  printf '错误: %s 阶段意外失败（脚本第 %s 行，退出码 %s）\n' "$STAGE" "$line" "$code" >&2
  if [ -n "$LOG_FILE" ]; then
    printf 'Stage: %s; line: %s; exit: %s\n' "$STAGE" "$line" "$code" >>"$LOG_FILE"
    printf '详细日志: %s\n' "$LOG_FILE" >&2
  fi
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

fetch() {
  local url=$1 out=$2
  local args=(--fail --location --retry 3 --connect-timeout 15 --silent --show-error)
  case "$url" in
    ftp://*|ftps://*) args+=(--netrc-optional) ;;
  esac
  curl "${args[@]}" ${CURL_EXTRA:-} -o "$out" "$url" 2>>"$LOG_FILE"
}

usage() {
  cat <<EOF
AIxCoding 安装器（macOS / Linux）

安装后的启动命令: aixcoding 或 aixcoding-cli

在线安装（默认生产渠道）:
  curl -fsSL ${BASE_URL%/}/install.sh | bash

用法:
  bash install.sh                            在线安装生产渠道当前版本
  bash install.sh --channel test             在线安装测试渠道当前版本
  bash install.sh --version v0.35.2          在线安装指定版本
  bash install.sh --from <包路径>            离线安装本地 ZIP 包
  bash install.sh --force                   重新安装（即使版本相同）

选项（也支持 --name=value 形式）:
  --base-url <地址>      镜像根地址
  --channel <prod|test>  选择生产或测试渠道（默认 prod）
  --version <版本>       安装指定完整版本
  --from <包路径>        从本地包安装，不访问网络
  --sha256 <摘要>        可选：用指定的 SHA-256 摘要校验安装包
  --force               强制重新安装
  -h, --help             显示本帮助

环境变量:
  AIXCODING_BASE_URL     镜像根地址（当前: ${BASE_URL}）
  AIXCODING_CHANNEL      默认渠道，prod 或 test（当前: ${CHANNEL}）
  CURL_EXTRA             追加给 curl 的额外参数（如代理）
EOF
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --base-url)    [ $# -ge 2 ] && [ -n "$2" ] || die "--base-url 需要非空地址"; BASE_URL=$2; shift 2 ;;
      --base-url=*)  BASE_URL=${1#--base-url=}; [ -n "$BASE_URL" ] || die "--base-url 需要非空地址"; shift ;;
      --version)     [ $# -ge 2 ] && [ -n "$2" ] || die "--version 需要非空版本号"; VERSION=$2; shift 2 ;;
      --version=*)   VERSION=${1#--version=}; [ -n "$VERSION" ] || die "--version 需要非空版本号"; shift ;;
      --channel)     [ $# -ge 2 ] && [ -n "$2" ] || die "--channel 需要 prod 或 test"; CHANNEL=$2; shift 2 ;;
      --channel=*)   CHANNEL=${1#--channel=}; [ -n "$CHANNEL" ] || die "--channel 需要 prod 或 test"; shift ;;
      --from)        [ $# -ge 2 ] && [ -n "$2" ] || die "--from 需要非空包路径"; FROM=$2; shift 2 ;;
      --from=*)      FROM=${1#--from=}; [ -n "$FROM" ] || die "--from 需要非空包路径"; shift ;;
      --sha256)      [ $# -ge 2 ] && [ -n "$2" ] || die "--sha256 需要非空摘要"; EXPECTED_SHA256=$2; shift 2 ;;
      --sha256=*)    EXPECTED_SHA256=${1#--sha256=}; [ -n "$EXPECTED_SHA256" ] || die "--sha256 需要非空摘要"; shift ;;
      --force)       FORCE=true; shift ;;
      -h|--help)     usage; exit 0 ;;
      *)             usage >&2; die "未知参数: $1" ;;
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
    *) die "无效渠道: ${CHANNEL}（只能是 prod 或 test）" ;;
  esac
  CHANNEL_FILE="${BASE_URL%/}/channels/cli/${CHANNEL}.txt"
}

detect_platform() {
  OS=$(uname -s)
  MACHINE=$(uname -m)
  case "$OS" in
    Darwin) ;;
    Linux) ;;
    MINGW*|MSYS*|CYGWIN*)
      die "检测到 Windows。请下载 aixcoding-cli-windows-x86_64-v<版本>-offline.zip，解压后在 PowerShell 运行: .\\aixcoding-cli.exe install"
      ;;
    *) die "不支持的系统: ${OS}" ;;
  esac
  case "$MACHINE" in
    x86_64|amd64) MACHINE=x86_64 ;;
    arm64|aarch64) MACHINE=aarch64 ;;
    *) die "不支持的处理器架构: ${MACHINE}" ;;
  esac
  if [ "$OS" = Darwin ] && [ "$MACHINE" = x86_64 ] && [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || true)" = 1 ]; then
    MACHINE=aarch64
  fi
  case "${OS}:${MACHINE}" in
    Darwin:x86_64)  PLATFORM=macos-x86_64 ;;
    Darwin:aarch64) PLATFORM=macos-aarch64 ;;
    Linux:x86_64)   PLATFORM=linux-x86_64 ;;
    Linux:aarch64)  PLATFORM=linux-aarch64 ;;
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
      *musl*) die "检测到 musl (Alpine)。AIxCoding 不支持 musl，请使用 glibc 发行版" ;;
    esac
    die "无法读取 libc 版本: ${ldd_output:-ldd 未返回信息}"
  fi
  ldd_first_line=${ldd_output%%$'\n'*}
  case "$ldd_output" in
    *musl*) die "检测到 musl (Alpine)。AIxCoding 不支持 musl，请使用 glibc 发行版" ;;
  esac
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

check_aixcoding_cli_command() {
  BIN_DIR="${HOME}/.local/bin"
  local name found
  for name in aixcoding aixcoding-cli; do
    for found in "$BIN_DIR/$name" "$(command -v "$name" 2>/dev/null || true)"; do
      [ -n "$found" ] || continue
      if [ ! -e "$found" ] && [ ! -L "$found" ]; then
        continue
      fi
      if [ "$found" -ef "$BIN_DIR/chrys" ]; then
        if [ "$found" = "$BIN_DIR/$name" ]; then OWNED_ALIASES="${OWNED_ALIASES}${name} "; fi
        continue
      fi
      # A dangling alias to our binary is repairable; other files are never replaced.
      if [ "$found" = "$BIN_DIR/$name" ] && [ -L "$found" ] && { [ "$(readlink "$found")" = chrys ] || [ "$(readlink "$found")" = "$BIN_DIR/chrys" ]; }; then
        continue
      fi
      if [ "$found" = "$BIN_DIR/$name" ] || [ ! -x "$BIN_DIR/chrys" ]; then
        die "${found} 属于其他安装，未作修改。请用原安装工具升级（如 uv tool upgrade iCode-TUI），或先卸载该命令再重试"
      fi
      EXTERNAL_COMMAND=$found
    done
  done
  if [ -x "$BIN_DIR/chrys" ]; then
    INSTALLED_VERSION=$("$BIN_DIR/chrys" --version 2>/dev/null </dev/null || true)
  fi
}

create_launch_commands() {
  local name target
  for name in aixcoding aixcoding-cli; do
    target="$BIN_DIR/$name"
    if [ -e "$target" ] || [ -L "$target" ]; then
      if [ "$target" -ef "$BIN_DIR/chrys" ]; then
        continue
      fi
      case "$OWNED_ALIASES" in
        *" $name "*) : ;;
        *)
          if [ ! -L "$target" ] || { [ "$(readlink "$target")" != chrys ] && [ "$(readlink "$target")" != "$BIN_DIR/chrys" ]; }; then
            die "${target} 属于其他安装，未作修改"
          fi
          ;;
      esac
    fi
    ln -sfn chrys "$target"
  done
}

skip_if_already_installed() {
  if [ "$FORCE" = false ] && [ -n "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" = "$VERSION" ]; then
    create_launch_commands
    verify_installed_command
    persist_path
    info "AIxCoding ${VERSION} 已安装，无需重复安装；如需重装请加 --force"
    print_finish
    exit 0
  fi
}

show_install_action() {
  if [ -z "$INSTALLED_VERSION" ]; then
    info "首次安装 AIxCoding ${VERSION}"
  elif [ "$INSTALLED_VERSION" = "$VERSION" ]; then
    info "重新安装 AIxCoding ${VERSION}"
  else
    info "更新 AIxCoding: ${INSTALLED_VERSION} → ${VERSION}"
  fi
}

obtain_archive() {
  if [ -n "$FROM" ]; then
    [ -f "$FROM" ] || die "包不存在: $FROM"
    ARCHIVE_NAME=$(basename -- "$FROM")
    case "$ARCHIVE_NAME" in
      icode-*) die "旧版安装包不支持经此脚本安装，请从镜像获取最新版 aixcoding-cli 制品" ;;
    esac
    case "$FROM" in
      *.zip) : ;;
      *) die "不支持的安装包格式: ${FROM}（仅支持 ZIP）" ;;
    esac
    ARCHIVE=$FROM
    info "使用本地安装包: ${ARCHIVE}"
    return 0
  fi

  need curl
  VERSION="${VERSION#v}"
  if [ -z "$VERSION" ]; then
    info "获取${CHANNEL_LABEL}当前版本号（${CHANNEL_FILE}）"
    local rc=0
    fetch "$CHANNEL_FILE" "${WORK_DIR}/channel.txt" || rc=$?
    [ "$rc" -eq 0 ] || die "无法获取 channels/cli/${CHANNEL}.txt（curl exit ${rc}）。请检查镜像地址与网络；若服务器已迁移或需指定其他地址，用 --base-url <地址> 或设 AIXCODING_BASE_URL=<地址> 后重试；也可用 --version 指定版本或 --from 离线安装"
    VERSION=$(sed -E 's/^[[:space:]]*[vV][[:space:]]*//; s/[[:space:]]*$//' "${WORK_DIR}/channel.txt" | tr -d '\r')
    [ -n "$VERSION" ] || die "channels/cli/${CHANNEL}.txt 内容为空（应为一行完整版本号，如 0.35.2）"
  fi
  [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([._-][[:alnum:]._-]+)?$ ]] || die "版本号格式无效: ${VERSION}（检查 channels/cli/${CHANNEL}.txt 或 --version）"

  skip_if_already_installed

  show_install_action
  ARCHIVE_NAME="aixcoding-cli-${PLATFORM}-v${VERSION}-offline.zip"
  ARCHIVE="${WORK_DIR}/${ARCHIVE_NAME}"
  info "下载 ${ARCHIVE_NAME}"
  local rc=0
  fetch "${BASE_URL%/}/releases/cli/${VERSION}/${ARCHIVE_NAME}" "$ARCHIVE" || rc=$?
  if [ "$rc" -ne 0 ]; then
    die "安装包下载失败（退出码 ${rc}）。请检查网络和发布版本；镜像变更可用 --base-url <地址> 或 AIXCODING_BASE_URL=<地址>"
  fi
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
  need unzip
  unzip -q "$ARCHIVE" -d "$EXTRACT_DIR" >>"$LOG_FILE" 2>&1 || die "ZIP 解压失败，请重新下载安装包"
  if [ -f "${EXTRACT_DIR}/aixcoding-cli.exe" ]; then
    die "这是 Windows 安装包。请在 Windows 上解压后运行 .\\aixcoding-cli.exe install"
  fi
  if [ ! -f "${EXTRACT_DIR}/aixcoding-cli" ]; then
    die "包内未找到根目录下的 aixcoding-cli 可执行文件；请核对安装包内容和平台"
  fi
  BINARY_PATH="${EXTRACT_DIR}/aixcoding-cli"
  chmod +x "$BINARY_PATH"
  if [ "$OS" = Darwin ]; then
    xattr -d com.apple.quarantine "$BINARY_PATH" 2>/dev/null || true
  fi
}

smoke_test() {
  info "运行包内二进制自检（首次运行会解包内嵌 Python 运行时，可能耗时数秒）"
  local new_version rc
  if new_version=$("$BINARY_PATH" --version 2>&1 </dev/null); then
    [ -n "$new_version" ] || die "包内 ./aixcoding-cli --version 没有输出，拒绝安装"
  else
    rc=$?
    printf '%s\n' "$new_version" >>"$LOG_FILE"
    die "安装包自检失败（退出码 ${rc}）。请确认包对应 ${PLATFORM}，且系统满足运行要求"
  fi
  if [ -n "$VERSION" ] && [ "$VERSION" != "$new_version" ]; then
    die "安装包版本 ${new_version} 与目标 ${VERSION} 不一致，拒绝安装"
  fi
  VERSION=$new_version
  if [ -n "$FROM" ]; then
    skip_if_already_installed
    show_install_action
  fi
}

run_official_install() {
  info "执行包内安装命令: ./aixcoding-cli install"
  local status=0
  "$BINARY_PATH" install </dev/null >>"$LOG_FILE" 2>&1 || status=$?
  if [ "$status" = 126 ]; then
    die "无法从 ${WORK_DIR} 运行安装程序。若该目录不允许执行程序，请将 TMPDIR 设为其他目录后重试"
  fi
  [ "$status" = 0 ] || die "./aixcoding-cli install 失败（退出码 ${status}）；请关闭正在运行的 AIxCoding 后重试"
}

verify_installed_command() {
  local name output
  for name in aixcoding aixcoding-cli; do
    [ -x "$BIN_DIR/$name" ] || die "安装后未找到可执行的 ${BIN_DIR}/${name}"
    if ! output=$("$BIN_DIR/$name" --version 2>&1 </dev/null); then
      printf '%s\n' "$output" >>"$LOG_FILE"
      die "${name} 启动验证失败"
    fi
    [ "$output" = "$VERSION" ] || die "${name} 版本验证失败（期望 ${VERSION}，实际 ${output}）"
  done
}

persist_path() {
  local shell_name added=false
  shell_name=$(basename "${SHELL:-/bin/bash}")
  case "$shell_name" in
    zsh) RC_FILE="$HOME/.zshrc" ;;
    *) RC_FILE="$HOME/.bashrc" ;;
  esac
  if ! grep -q '\.local/bin' "$RC_FILE" 2>/dev/null; then
    if ! printf '\n# Added by AIxCoding installer\nexport PATH="$HOME/.local/bin:$PATH"\n' 2>>"$LOG_FILE" >> "$RC_FILE"; then
      die "无法写入 ${RC_FILE} 配置 PATH，请检查文件类型与写入权限"
    fi
    added=true
  fi
  if [ "$shell_name" != zsh ] && [ -f "$HOME/.bash_profile" ] && ! grep -q 'bashrc' "$HOME/.bash_profile" 2>/dev/null; then
    if ! printf '[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"\n' 2>>"$LOG_FILE" >> "$HOME/.bash_profile"; then
      die "无法写入 ~/.bash_profile 配置 PATH，请检查文件类型与写入权限"
    fi
    added=true
  fi
  if [ "$added" = true ]; then
    info "已将 ~/.local/bin 写入 ${RC_FILE}（新开终端自动生效）"
  else
    info "PATH 配置已存在于 ${RC_FILE}，无需修改"
  fi
}

print_finish() {
  info "安装就绪。新开终端后运行: aixcoding 或 aixcoding-cli"
  if [ -n "$EXTERNAL_COMMAND" ]; then
    warn "PATH 中另有外部命令 ${EXTERNAL_COMMAND}，已保留；请使用 ${BIN_DIR}/aixcoding 或 ${BIN_DIR}/aixcoding-cli"
  fi
}

main() {
  STAGE="解析参数"
  parse_args "$@"
  STAGE="选择渠道"
  resolve_channel
  [ -n "${HOME:-}" ] || die "HOME 未设置，无法确定当前用户的安装目录"
  STAGE="检测平台"
  detect_platform
  STAGE="检查 libc"
  check_glibc
  STAGE="检查命令冲突"
  check_aixcoding_cli_command
  STAGE="创建临时目录"
  WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/aixcoding-install.XXXXXX") || die "无法创建临时目录，请检查 TMPDIR 的空间和权限"
  trap 'code=$?; rm -rf "$WORK_DIR"; if [ "$code" -eq 0 ] && [ -n "$LOG_FILE" ]; then rm -f "$LOG_FILE"; fi' EXIT

  LOG_FILE=$(mktemp "${TMPDIR:-/tmp}/aixcoding-install-log.XXXXXX")
  chmod 600 "$LOG_FILE"
  STAGE="获取安装包"
  obtain_archive
  STAGE="校验安装包"
  verify_archive
  STAGE="解压安装包"
  extract_archive
  STAGE="运行二进制自检"
  smoke_test
  STAGE="执行安装"
  run_official_install
  STAGE="创建启动命令"
  create_launch_commands
  STAGE="验证安装命令"
  verify_installed_command
  STAGE="配置 PATH"
  persist_path
  STAGE="完成安装"
  print_finish
}

main "$@"
