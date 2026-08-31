#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <PEP440-VERSION>" >&2
  exit 2
}

if [ "$#" -ne 1 ]; then
  usage
fi

version="$1"

if ! [[ "$version" =~ ^[0-9]+(\.[0-9]+)+([abc][0-9]+)?(\.post[0-9]+)?(\.dev[0-9]+)?$ ]]; then
  echo "Invalid PEP 440 version: $version" >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
pyproject="$root/src/python/pyproject.toml"
init="$root/src/python/whero/doctidex/__init__.py"

for file in "$pyproject" "$init"; do
  if [ ! -f "$file" ]; then
    echo "Missing version source: $file" >&2
    exit 1
  fi
done

DOCTIDEX_RELEASE_VERSION="$version" perl -pi -e \
  's/^version = "[^"]+"/version = "$ENV{DOCTIDEX_RELEASE_VERSION}"/' \
  "$pyproject"

DOCTIDEX_RELEASE_VERSION="$version" perl -pi -e \
  's/^__version__ = "[^"]+"/__version__ = "$ENV{DOCTIDEX_RELEASE_VERSION}"/' \
  "$init"

echo "$version"
