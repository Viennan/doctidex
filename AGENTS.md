# Doctidex Repository Guide

## Start here

- First read [docs/dev/architecture/overview.md](docs/dev/architecture/overview.md) before starting work.
- Start a non-trivial repository change from an Issue Note proposal. See
  [docs/dev/issues/AGENTS.md](docs/dev/issues/AGENTS.md).

## Repository Overview

`doctidex` is a directory-tree structure standard that keeps Markdown and ordinary files readable while providing stable navigation for humans, agents, and programs. It supports repositories as navigable, traceable knowledge bases, including controlled links to fixed Git revisions in other repositories.

Version 2.x.x is the active development line.

## Directory structure

```text
.
├── AGENTS.md
├── docs/               # Repository documentation and scoped guidance.
│   ├── AGENTS.md
│   ├── dev/            # Development, architecture, cookbook, and issue documentation.
│   │   └── issues/
│   │       └── AGENTS.md
│   └── user/           # User-facing documentation for the user surface.
├── scripts/            # Repository-local helper scripts.
├── skills/             # Twin Skills shipped with the CLI.
└── src/                # Source code.
    ├── AGENTS.md
    └── python/         # Python implementation and tests.
```

## Scoped guidance

Scoped `AGENTS.md` files:

- `docs/AGENTS.md`
- `docs/dev/issues/AGENTS.md`
- `src/AGENTS.md`

Treat a **scoped-AGENTS.md** as the root `AGENTS.md` scoped to its path. Read every **scoped-AGENTS.md** on the path you access.

## Maintenance routing

- When a non-trivial repository change is made, update [README.md](README.md) only to introduce or refresh the
  product's distinctive, most competitive capabilities, and keep those statements current in the same change.

Use [doctidex-scaffolding-builder](.agents/skills/doctidex-scaffolding-builder/SKILL.md) to keep this directory diagram and the scoped `AGENTS.md` list synchronized when either changes.

Use [doctidex-twin-skill-maintenance](.agents/skills/doctidex-twin-skill-maintenance/SKILL.md) when:

- adding, removing, or renaming a `docs/user/*.md` file;
- changing `skills/doctidex-git/SKILL.md` or its `references/`;
- changing CLI behavior that affects how an agent follows a Twin Skill, including a new core capability, a
  boundary-expanding behavior change, or a breaking change;
- rebuilding `_skill_data` for packaging.

Use [doctidex-release](.agents/skills/doctidex-release/SKILL.md) when building, validating, or publishing a
`doctidex-git` release, including creating release tags, building the wheel, generating release notes, and running
alpha tests.

## Python Engineering Conventions

- Use the project-root `.venv` as the default Python runtime for all Python code and tools in this repository. Create it before use when it does not exist.
- Develop all Python code in this repository against Python 3.12 or later.
