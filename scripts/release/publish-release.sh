#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <TAG> <WHEEL> <NOTES-FILE> <PRERELEASE>" >&2
  exit 2
}

if [ "$#" -ne 4 ]; then
  usage
fi

tag="$1"
wheel="$2"
notes_file="$3"
prerelease="$4"

if [ ! -f "$wheel" ]; then
  echo "Wheel not found: $wheel" >&2
  exit 1
fi

base_tag="${tag%%a[0-9]*}"
target="release/${base_tag}"
args=(release create "$tag" "$wheel" --target "$target" --title "doctidex-git $tag")

if [ "$prerelease" = "1" ] || [ "$prerelease" = "true" ]; then
  args+=(--prerelease)
fi

if [ -n "$notes_file" ] && [ -f "$notes_file" ]; then
  args+=(--notes-file "$notes_file")
else
  args+=(--notes "doctidex-git $tag")
fi

gh "${args[@]}"
