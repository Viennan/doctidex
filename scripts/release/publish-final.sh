#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <VERSION> [PREVIOUS-TAG]" >&2
  exit 2
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
fi

version="$1"
previous="${2:-}"

if ! [[ "$version" =~ ^[0-9]+(\.[0-9]+)+$ ]]; then
  echo "Expected a final PEP 440 version such as 2.0.0: $version" >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
branch="release/v${version}"
tag="v${version}"

gh auth status >/dev/null 2>&1 || {
  echo "GitHub authentication is not available; fix gh auth before publishing." >&2
  exit 1
}

if [ "$(git -C "$root" branch --show-current)" != "$branch" ]; then
  echo "Switch to $branch before publishing the final release." >&2
  exit 1
fi

"$root/scripts/release/set-version.sh" "$version"

if ! git -C "$root" diff --quiet; then
  git -C "$root" add src/python/pyproject.toml src/python/whero/doctidex/__init__.py
  git -C "$root" commit -m "Set version to $version"
fi

git -C "$root" push -u origin "$branch"
wheel="$("$root/scripts/release/build-wheel.sh" "$version")"

if [ -z "$previous" ]; then
  previous="$(git -C "$root" tag --list "v${version%%.*}*" --sort=-v:refname |
    grep -v "^v${version}$" | head -n 1 || true)"
  if [ -z "$previous" ]; then
    previous="$(git -C "$root" rev-list --max-parents=0 HEAD)"
  fi
fi

notes="$(mktemp /tmp/doctidex-release-notes.XXXXXX)"
trap 'rm -f "$notes"' EXIT
"$root/scripts/release/generate-release-notes.sh" "$previous" "$tag" > "$notes"

"$root/scripts/release/publish-release.sh" "$tag" "$wheel" "$notes" 0
