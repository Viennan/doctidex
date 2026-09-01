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
venv_python="$root/.venv/bin/python"
src_python="$root/src/python"
wheel="$src_python/dist/whero_doctidex-${version}-py3-none-any.whl"

if [ ! -x "$venv_python" ]; then
  echo "Project virtual environment not found: $venv_python" >&2
  exit 1
fi

"$venv_python" "$root/scripts/validate-version-alignment.py"

(
  cd "$src_python"
  "$venv_python" -m pip wheel . --no-deps --no-build-isolation --no-cache-dir --wheel-dir dist
)

if [ ! -f "$wheel" ]; then
  echo "Expected wheel not found: $wheel" >&2
  exit 1
fi

echo "$wheel"
