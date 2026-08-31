#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <VERSION>" >&2
  exit 2
}

if [ "$#" -ne 1 ]; then
  usage
fi

version="$1"

if ! [[ "$version" =~ ^[0-9]+(\.[0-9]+)+a[0-9]+$ ]]; then
  echo "Expected an alpha PEP 440 version such as 2.0.0a1: $version" >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
branch="release/v${version%%a[0-9]*}"
tag="v${version}"

gh auth status >/dev/null 2>&1 || {
  echo "GitHub authentication is not available; fix gh auth before publishing." >&2
  exit 1
}

if [ "$(git -C "$root" branch --show-current)" != "$branch" ]; then
  echo "Switch to $branch before publishing alpha." >&2
  exit 1
fi

"$root/scripts/release/set-version.sh" "$version"

if ! git -C "$root" diff --quiet -- src/python/pyproject.toml src/python/whero/doctidex/__init__.py; then
  git -C "$root" add src/python/pyproject.toml src/python/whero/doctidex/__init__.py
  git -C "$root" commit -m "Set version to $version"
fi

git -C "$root" push -u origin "$branch"
wheel="$("$root/scripts/release/build-wheel.sh" "$version" | tail -n 1)"

smoke_dir="$(mktemp -d /tmp/doctidex-alpha-smoke.XXXXXX)"
trap 'rm -rf "$smoke_dir"' EXIT
python3 -m venv "$smoke_dir"
"$smoke_dir/bin/pip" install --no-cache-dir "$wheel"
"$smoke_dir/bin/doctidex-git" --help >/dev/null

"$root/scripts/release/publish-release.sh" "$tag" "$wheel" "" 1
