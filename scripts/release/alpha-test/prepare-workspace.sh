#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 <BASE> <VERSION>" >&2
  exit 2
}

if [ "$#" -ne 2 ]; then
  usage
fi

base="$1"
version="$2"

if ! [[ "$version" =~ ^[0-9]+(\.[0-9]+)+([abc][0-9]+)?(\.post[0-9]+)?(\.dev[0-9]+)?$ ]]; then
  echo "Invalid PEP 440 version: $version" >&2
  exit 2
fi

mkdir -p "$base"
workdir="$(mktemp -d "$base/alpha-${version}-XXXXXX")"

git init -q "$workdir"
python3 -m venv "$workdir/.venv"
mkdir -p "$workdir/bin"

cat > "$workdir/bin/doctidex-alpha" <<'EOF'
#!/usr/bin/env bash

set -u

workdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log="$workdir/alpha-command.log"

start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

env "DOCTIDEX-GIT-HOME=$workdir/.doctidex-home" "$workdir/.venv/bin/doctidex-git" "$@"
code=$?

printf '%s %s %s\n' "$start" "$code" "$*" >> "$log"
exit "$code"
EOF

chmod +x "$workdir/bin/doctidex-alpha"
: > "$workdir/alpha-command.log"

wheel_url="${DOCTIDEX_ALPHA_WHEEL_URL:-<WHEEL-URL>}"
git_tag="${DOCTIDEX_ALPHA_TAG:-v${version}}"

cat <<EOF
ALPHA_WORKDIR=$workdir
ALPHA_VERSION=$version

Fixed codex prompt:
---
Work only inside $workdir. It is already a Git repository with a .venv.
Do not use pipx.
Install the doctidex-git alpha wheel from $wheel_url into $workdir/.venv.
Install the bundled Twin Skill into $workdir/.agents/skills.
Use $workdir/bin/doctidex-alpha for every doctidex-git command; it supplies DOCTIDEX-GIT-HOME.
Initialize the workspace, then import the alpha tag $git_tag as a tracked Installation.
---
EOF
