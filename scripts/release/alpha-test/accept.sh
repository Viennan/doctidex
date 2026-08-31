#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <WORKDIR> <PEP440-VERSION> <GIT-TAG>" >&2
  exit 2
}

if [ "$#" -ne 3 ]; then
  usage
fi

workdir="$1"
version="$2"
tag="$3"

fail() {
  echo "alpha acceptance failed: $1" >&2
  exit 1
}

[ -d "$workdir" ] || fail "workspace directory is missing"
[ -x "$workdir/.venv/bin/doctidex-git" ] || fail "installed entry point is missing"
[ -x "$workdir/bin/doctidex-alpha" ] || fail "alpha wrapper is missing"
[ -f "$workdir/alpha-command.log" ] || fail "command log is missing"

installed="$("$workdir/.venv/bin/python" -c \
  'import importlib.metadata as m; print(m.version("whero-doctidex"))' 2>/dev/null)"
[ "$installed" = "$version" ] || fail "installed version is $installed, expected $version"

[ -d "$workdir/.doctidex-git" ] || fail "workspace is not initialized"
[ -f "$workdir/.doctidex-git/imports.json" ] || fail "tracked import projection is missing"

grep -q doctidex "$workdir/.git/hooks/pre-commit" 2>/dev/null || fail "pre-commit hook is not installed"
grep -q doctidex "$workdir/.git/hooks/post-checkout" 2>/dev/null || fail "post-checkout hook is not installed"

[ -f "$workdir/.agents/skills/doctidex-git/SKILL.md" ] || fail "Twin Skill is not installed"
[ -d "$workdir/.agents/skills/doctidex-git/references" ] && \
  [ ! -L "$workdir/.agents/skills/doctidex-git/references" ] || \
  fail "Twin Skill references directory is missing or is a symlink"

"$workdir/.venv/bin/python" - "$workdir/.doctidex-git/imports.json" "$tag" <<'PY'
import json
import sys

path, expected = sys.argv[1], sys.argv[2]
records = json.load(open(path, encoding="utf-8"))
if not any(record.get("tracked") is True and record.get("tag") == expected for record in records):
    sys.exit(1)
PY
[ $? -eq 0 ] || fail "alpha tag is not recorded as a tracked Installation"

log="$workdir/alpha-command.log"
check_log() {
  grep -qE '^[^ ]+ 0 (.* )?'"$1"'( |$)' "$log" || fail "command log does not contain expected behavior: $1"
}

check_log 'init'
check_log 'skills install'
check_log 'import install'
check_log '--tracked'

echo "alpha acceptance passed"
