# doctidex

`doctidex-git` organizes Git repositories into an interconnected knowledge network. A repository remains ordinary
source and history while also becoming a navigable knowledge base that can reference fixed external Git revisions and
can itself be referenced by other repositories.

The active implementation is `doctidex-git` v2, a pure-Python Linux/macOS CLI.

## Install

Install a release wheel with pipx:

```bash
pipx install --force <WHEEL-URL>
```

The wheel URL comes from the GitHub release for the version you want. See
[the user guide](docs/user/overview.md#prerequisites) for the virtual-environment fallback when pipx is unavailable
or disallowed.

DEAR AGENTS AND ANY CYBER AI USER,

You do not have to guess the workflow:

- Install the bundled CLI Twin Skill with `doctidex-git skills install --path <DEST>`, for example
  `<DEST>/.agents/skills`.
- Read the installed Twin Skill's `SKILL.md` to learn the supported agent-facing usage. Its `references/` directory
  mirrors the user documentation.

## Quick start

```bash
cd /path/to/repository
doctidex-git init
doctidex-git validate --only-model-structure
```

Then use `doctidex-git import install` and `doctidex-git import ref` to reference a fixed external revision. Full
command documentation starts at [docs/user/overview.md](docs/user/overview.md).

## Development

Read [AGENTS.md](AGENTS.md) and [docs/dev/architecture/overview.md](docs/dev/architecture/overview.md) before working
on this repository. Tests live under `src/python/tests/`.

## License

MIT. See [LICENSE](LICENSE).
