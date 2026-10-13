#!/usr/bin/env bash
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

# Assemble the files that are copied together to the internal release mirror.
set -euo pipefail

artifacts_dir=${1:-artifacts}
output_dir=${2:-dist/release-bundle}
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd "$script_dir/.." && pwd)

[ -d "$artifacts_dir" ] || { echo "Missing artifact directory: $artifacts_dir" >&2; exit 1; }
mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd)
[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
  echo "Output directory is not empty: $output_dir" >&2
  exit 1
}
shopt -s nullglob

artifact_dirs=("$artifacts_dir"/aixcoding-cli-*/)
[ ${#artifact_dirs[@]} -gt 0 ] || { echo "No binary artifacts found in $artifacts_dir" >&2; exit 1; }

version=""
for dir in "${artifact_dirs[@]}"; do
  artifact=$(basename "$dir")
  without_flavor=${artifact%-*}
  artifact_version=${without_flavor#*-v}
  if [ "$artifact_version" = "$without_flavor" ] || [ -z "$artifact_version" ]; then
    echo "Cannot read version from artifact name: $artifact" >&2
    exit 1
  fi
  if [ -n "$version" ] && [ "$version" != "$artifact_version" ]; then
    echo "Mixed artifact versions: v$version and v$artifact_version" >&2
    exit 1
  fi
  version=$artifact_version

  if [ -f "$dir/aixcoding-cli.exe" ]; then
    (cd "$dir" && zip -q "$output_dir/${artifact}.zip" aixcoding-cli.exe)
  elif [ -f "$dir/aixcoding-cli" ]; then
    # Actions artifacts do not preserve executable permissions.
    chmod +x "$dir/aixcoding-cli"
    COPYFILE_DISABLE=1 tar -czf "$output_dir/${artifact}.tar.gz" -C "$dir" aixcoding-cli
  else
    echo "Missing aixcoding-cli binary in artifact: $artifact" >&2
    exit 1
  fi
done

wheel_files=("$artifacts_dir"/wheel/*.whl)
[ ${#wheel_files[@]} -gt 0 ] || { echo "No wheel artifact found in $artifacts_dir/wheel" >&2; exit 1; }
wheel_name=$(basename "${wheel_files[0]}")
wheel_version=${wheel_name#chrys-}
wheel_version=${wheel_version%%-*}
if [ "$wheel_version" = "$wheel_name" ] || [[ "$version" != "$wheel_version" && "$version" != "$wheel_version"-dev-* ]]; then
  echo "Binary version v$version does not match wheel $wheel_name" >&2
  exit 1
fi
cp "${wheel_files[@]}" "$output_dir/"
cp "$script_dir/install.sh" "$output_dir/install.sh"
cp "$repo_dir/release/INSTALL.md" "$output_dir/INSTALL.md"
printf 'v%s\n' "$version" > "$output_dir/latest.txt"

echo "Release bundle ready: $output_dir (v$version)"
