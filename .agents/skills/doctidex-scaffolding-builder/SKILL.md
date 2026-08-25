---
name: doctidex-scaffolding-builder
description: Maintain Doctidex's repository-local Agent scaffolding, including the AGENTS.md hierarchy, repository Skills, and related guidance, keeping it coherent and discoverable as the repository evolves. Use before changing this scaffolding.
---

# Doctidex Scaffolding Builder

This is a guide, not a script. Use judgment to keep the repository's vibe coding scaffolding coherent, discoverable, and proportionate to the work it supports.

## Scope

This Skill governs changes to `AGENTS.md`, **scoped-AGENTS.md**, `.agents/skills/`, Skill metadata, and closely related repository-local Agent scaffolding. Before changing these artifacts, read the applicable `AGENTS.md` files and relevant existing Skills.

## Language

Write all scaffolding-related documentation, instructions, and prompts in English.

## Terminology

Use fixed terms for representative, core, or key concepts in `AGENTS.md` files and Skills. Prefer a short bold term, such as **scoped-AGENTS.md**, over repeating the same explanation.

A root `AGENTS.md` is repository-wide. A **scoped-AGENTS.md** is an `AGENTS.md` placed in a subdirectory to provide directory-scoped guidance.

Reference a term defined elsewhere with `[term](relative-link)`. For Skills, this is also how one Skill may cite another Skill's term or guidance.

## AGENTS.md

Use the root `AGENTS.md` for repository-wide identity, stable authority locations, and routing into scoped guidance. Add a **scoped-AGENTS.md** only when a directory needs durable local rules that cannot remain clear at the root. Keep scoped files shallow and make the local scope evident from their directory.

Typical scoped guidance includes documentation conventions below a documentation directory, code conventions at a code root or its parent, and Skill routing that only applies to one area. Let a **scoped-AGENTS.md** supplement or narrow the applicable parent guidance; explain any intentional exception where it is declared.

When an `AGENTS.md` file, including a **scoped-AGENTS.md**, would contain a large explicit write-oriented workflow, move that workflow into a dedicated Skill or merge it into an existing Skill serving the same subject. Keep the `AGENTS.md` as routing and orchestration: state when and how to use the Skill, and provide enough detail beyond the Skill's frontmatter description to select and sequence the workflow. Keep trigger conditions in the `AGENTS.md`; move only execution rules, operation steps, and checks into the Skill.

The root `AGENTS.md` must include a directory-structure diagram. By default, show `docs` and `src` with two levels and brief descriptions; always show every path containing a **scoped-AGENTS.md** or `AGENTS.md` file, without adding a description for those files. The root `AGENTS.md` must also state that a **scoped-AGENTS.md** is the root `AGENTS.md` scoped to that path, and that agents must read every **scoped-AGENTS.md** on the access path.

Attach Skill triggers in `AGENTS.md` and **scoped-AGENTS.md** to concrete local actions or workflows. Each trigger must add detail beyond the Skill's broad, high-compression frontmatter `description`, not restate it. Prefer meaningful orchestration—use Skill A for a required pre-step, then Skill B to create the object—only when that sequence is not already a generic workflow inside Skill A or Skill B.

## Skills

Repository-local Skill directories use the `doctidex-` prefix and contain a `SKILL.md` with concise, discriminating frontmatter. Start every Skill prompt by making clear that it is a guide, not a script. State the task boundary, the non-obvious local constraints, and only the workflow detail that changes an Agent's decisions.

Add metadata, references, scripts, or assets only when they serve a concrete use. Cross-reference Skills, `AGENTS.md`, and repository documents when that helps keep Agent behavior consistent; links may point to internal or external authority.

When creating or adapting a Skill, keep its stated scope general enough for foreseeable repository evolution. Do not narrow a rule to a current language, path, or artifact type unless the narrower boundary is intentional; if a wording could hide other in-scope code or documents, generalize it.

Do not add a standalone "Related Skills" section merely to list related work. Reference another Skill at the concrete step or check that requires it, and state what that Skill is used to do there.

## Runtime Context

When introducing or adapting a Skill, identify its real runtime assumptions: persistent work locations, path bases, required tools, source documents, generated artifacts, or state that must survive a turn. Make those assumptions usable in the surrounding scaffolding. The information may be conveyed naturally through repository layout, a scoped `AGENTS.md`, linked context, or the Skill itself; choose the least intrusive form that keeps the Skill operational.

Do not add ceremonial instructions or duplicate repository data into a Skill when a concise reference to its authority is sufficient.

## Review

Before handoff, verify that:

- the scope can be discovered from applicable Agent guidance;
- **scoped-AGENTS.md** guidance does not conflict;
- Skill names use the required prefix;
- cross-references resolve;
- every affected reference and link is valid;
- skill trigger timing text in `AGENTS.md` and **scoped-AGENTS.md** files has not regressed or retained outdated trigger descriptions;
- the result is complete without unnecessary process text;
- changed scaffolding prose and its surrounding context meet the repository prose standard, using [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md).
