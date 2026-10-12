#!/usr/bin/env bash
# Rebuild the zh-Hans i18n catalog artifacts (pot -> po -> mo) and verify.
#
# Fixes the CI failure "MO translation content is stale relative to the PO":
# a merge can bring in a .po compiled from a different source than the tracked
# .mo, so the whole chain is rebuilt and the oracle tests re-run before push.
#
# Usage:  ./scripts/rebuild_mo.sh
# Stages nothing: review the artifact diff it prints at the end and commit it
# together with the change that caused it (repo rule: i18n artifacts ship in
# the same commit as their source change).

set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/5 extract（源码 msg() -> locales/chrys.pot） =="
uv run python scripts/i18n.py extract

echo "== 2/5 update（pot 合入 locales/zh-Hans/.../chrys.po） =="
uv run python scripts/i18n.py update

echo "== 3/5 compile（po -> src/.../_catalogs/.../chrys.mo，原子替换） =="
uv run python scripts/i18n.py compile

echo "== 4/5 check（新鲜度与安全门禁） =="
uv run python scripts/i18n.py check

echo "== 5/5 oracle 测试（CI 上挂的那个逐条语义比对） =="
uv run pytest -q -n0 tests/foundation/i18n/test_catalog_oracle.py

echo
echo "== 生成产物变更（review 后随本次改动一起提交） =="
git status -s -- locales src/chrys/foundation/i18n
