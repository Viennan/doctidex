#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <PREVIOUS-TAG> <FINAL-TAG>" >&2
  exit 2
}

if [ "$#" -ne 2 ]; then
  usage
fi

previous="$1"
final="$2"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
owner_repo="$(git -C "$root" remote get-url origin 2>/dev/null |
  sed -nE 's#^.*github\.com[:/]([^/]+)/([^/]+)$#\1/\2#p')"
owner_repo="${owner_repo%.git}"

if [ -z "$owner_repo" ]; then
  owner_repo="OWNER/REPOSITORY"
fi

previous_files="$(git -C "$root" ls-tree -r --name-only "$previous" docs/dev/issues/implemented |
  awk -F/ '$5 ~ /^(feature|architecture|bug-fix)$/' | sort)"
final_files="$(git -C "$root" ls-tree -r --name-only "$final" docs/dev/issues/implemented |
  awk -F/ '$5 ~ /^(feature|architecture|bug-fix)$/' | sort)"
new_files="$(comm -13 <(printf '%s\n' "$previous_files") <(printf '%s\n' "$final_files"))"

echo "## What changed"

for class in feature architecture bug-fix; do
  class_files="$(printf '%s\n' "$new_files" | awk -F/ -v class="$class" '$5 == class { print }')"
  if [ -n "$class_files" ]; then
    printf '\n### %s\n\n' "$class"
    while IFS= read -r file; do
      title="$(git -C "$root" show "$final:$file" 2>/dev/null | sed -n '1s/^# Issue Note: //p')"
      if [ -z "$title" ]; then
        title="$(basename "$file")"
      fi
      url="https://github.com/${owner_repo}/blob/${final}/${file}"
      echo "- [${title}](${url})"
    done <<< "$class_files"
  fi
done
