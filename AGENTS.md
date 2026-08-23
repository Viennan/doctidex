# Doctidex Repository Guide

First read `docs/dev/architecture/` before starting work.

Start a non-trivial repository change from an Issue Note proposal. See [docs/dev/issues/AGENTS.md](docs/dev/issues/AGENTS.md).

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
└── src/                # Source code.
    ├── AGENTS.md
    └── python/         # Python implementation and tests.
```

Scoped `AGENTS.md` files:

- `AGENTS.md`
- `docs/AGENTS.md`
- `docs/dev/issues/AGENTS.md`
- `src/AGENTS.md`

Treat a **scoped-AGENTS.md** as the root `AGENTS.md` scoped to its path. Read every **scoped-AGENTS.md** on the path you access.

Use [doctidex-scaffolding-builder](.agents/skills/doctidex-scaffolding-builder/SKILL.md) to keep this directory diagram and the scoped `AGENTS.md` list synchronized when either changes.

## Python Engineering Conventions

- Use the project-root `.venv` as the default Python runtime for all Python code and tools in this repository. Create it before use when it does not exist.
- Develop all Python code in this repository against Python 3.12 or later.
