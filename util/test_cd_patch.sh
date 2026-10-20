#!/usr/bin/env bash
# Verify the cd.yml PyApp distribution patch end-to-end with real perl:
# extracts the unlock s/// one-liner and the two guard perl -0ne regexes
# from cd.yml, applies them to a mock distribution.rs, and asserts the
# patched code passes both guards.
set -euo pipefail
cd "$(dirname "$0")"

CD=../.github/workflows/cd.yml

# Extract line: s/\n    FileExt::unlock\(\&lock_file\)/.../;
UNLOCK_LINE=$(grep -F 'FileExt::unlock\(\&lock_file\)/' "$CD" | grep -F 's/\n' | head -1 | sed 's/^ *//')
# Extract guard lines from the if-chain.
GUARD1=$(grep -F 'install_project\(\)\?;\n    \}' "$CD" | head -1 | sed 's/^ *//;s/^|| ! //;s/ *\\$//;s|src/distribution\.rs$|dist_mock.rs|')
GUARD2=$(grep -F 'ensure_runtime_aliases\(\) \{' "$CD" | grep -F 'FileExt::unlock' | head -1 | sed 's/^ *//;s/^|| ! //;s/; then$//;s|src/distribution\.rs$|dist_mock.rs|')

cat > dist_mock.rs <<'EOF'
pub fn run_project() -> Result<()> {
    let mut command = python_command(&app::python_path());
    install_project()?;
    FileExt::unlock(&lock_file)
}
EOF

eval "perl -0pi -e '$UNLOCK_LINE' dist_mock.rs"
echo "--- patched dist_mock.rs ---"
cat dist_mock.rs

eval "$GUARD1" && echo "guard1 ok"
eval "$GUARD2" && echo "guard2 ok"
echo "ALL OK"
