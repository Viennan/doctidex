# doctidex

[中文说明](README.zh-CN.md)

doctidex is a directory-tree structure standard with a Git-oriented implementation for reading,
validating, and maintaining doctidex content. It keeps ordinary files and Markdown readable while
giving humans, agents, and programs stable navigation and observable structure.

## Origin and direction

doctidex began with a cross-repository problem: a developer's knowledge is often scattered across
many Git repositories, even when those repositories collectively describe one body of experience.
The long-term direction is to let that knowledge form an interconnected, traceable network rather
than leave each repository isolated.

This matters especially for AI-assisted development. When work begins in a new repository, an agent
needs a reviewable way to follow references to earlier repositories and understand the relevant
knowledge, practices, design patterns, and preferences behind the current work. A Git repository
with clear navigation and context can therefore act as a self-explaining knowledge base.

Today, doctidex provides the auditable foundation for that direction: readable indexes and
progressive navigation within a tree, plus fixed-revision external snapshots and presentations for
connecting Git content. It does not automatically discover, aggregate, or inject knowledge from all
repositories; people and agents retain control over which context is recorded and followed.

## Inspiration

The project is strongly inspired by Google's [Open Knowledge Format (OKF)](spec/refs/okf-v0.1.md),
especially its use of ordinary directories, Markdown, and minimal structural conventions for
human- and agent-readable knowledge. doctidex extends those ideas for its own Git-oriented use
cases and does not claim strict OKF format compatibility.

## What it provides

- A small protocol for indexes, links, local configuration, and reachability.
- `doctidex-git` workflows for protocol validation, fixed-commit external content, presentations,
  checkout coordination, and optional isolated worktrees.
- Human-readable output and versioned JSON results for agent and program integration.

## Typical use

Use doctidex when a repository needs a navigable knowledge or documentation tree, or when an agent
must read and maintain external Git snapshots without hiding the surrounding files from native tools.
Native Git, filesystem, search, Markdown, and delivery workflows remain available.

## Install `doctidex-git` and its agent bundle

The Python distribution requires CPython `>=3.11`. Choose the target `doctidex-git` version before
installing; replace `TARGET_DOCTIDEX_GIT_VERSION` below with that user-supplied version. The matching
repository tag has a `v` prefix.

```text
python -m pip install --no-input \
  "whero-doctidex @ git+https://github.com/Viennan/doctidex.git@v<TARGET_DOCTIDEX_GIT_VERSION>#subdirectory=impls/libs/python"
```

### Make the Published Skills available

The Python distribution provides the `doctidex-git` console script. The Published agent bundle is a
separate checkout of the same tag, so the code and Skills always come from the same selected release:

```text
git clone --depth 1 --branch v<TARGET_DOCTIDEX_GIT_VERSION> \
  https://github.com/Viennan/doctidex.git doctidex-agent-bundle
```

Import the following directory with the agent host's native plugin or Skill registration mechanism:

```text
doctidex-agent-bundle/impls/agent-plugins/doctidex-git/skills/
```

The bundle's portable content is the four `SKILL.md` workflows. A host without plugin or Skill
registration can instead give the agent the applicable `SKILL.md` directly, starting with
`doctidex-git-overview`. The bundle also includes `.codex-plugin` metadata for Codex, but that
metadata and any Codex-specific command are optional; they are not required by other agent hosts.

After installation, verify the selected environment exposes the console script:

```text
doctidex-git --help
```

### Choose the shared cache location

The optional `DOCTIDEX_GIT_CACHE` environment variable lets the user choose an absolute, writable
shared cache path. Set it in every CLI, automation, or host Git process that must share the cache.
The user owns this environment choice; an agent does not write shell profiles or project settings for
it.

```text
export DOCTIDEX_GIT_CACHE=/absolute/path/to/doctidex-cache
```

When unset, the installed variant uses its platform default cache location.

## Continue

Start with the [repository map](index.md) to find the protocol, design documentation, implementations,
and installed agent surfaces. The project is designed to be explored and developed with agent
assistance.
