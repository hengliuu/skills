---
name: claude-md-author
description: Write, audit, and slim down agent context files — CLAUDE.md, AGENTS.md, and per-directory variants. Use when the user asks to create, check, audit, review, improve, fix, shorten, or slim a CLAUDE.md / AGENTS.md, or mentions "project memory", "agent context file", or "context file maintenance". Enforces a tight instruction budget, WHAT/WHY/HOW structure, and universal-applicability rules so every line earns its place.
---

# CLAUDE.md / AGENTS.md Author

Agent context files (`CLAUDE.md`, `AGENTS.md`, and their per-directory variants) are the
**highest-leverage files in a repo**: they are injected into every task. A wasted or wrong line
degrades *every* future session. Treat them accordingly — hand-craft every line, keep them short,
and only include what applies to all work in that scope.

This skill both **authors** new context files and **audits/slims** existing ones. It can write to
files, but only after showing a plan and getting approval.

## The Golden Rules

These are non-negotiable. Apply them when writing and when judging an existing file.

1. **Highest-leverage, so hand-crafted.** Never auto-generate the file with `/init` or similar and
   ship it as-is. Every line is reviewed by a human-in-the-loop.
2. **Less is more — respect the instruction budget.** Anthropic's own guidance targets **under 200
   lines** per CLAUDE.md file (longer measurably reduces adherence). This team's bar is stricter —
   **under 100 lines** for a root file, great teams **under 60**, hard ceiling 300 — because an LLM
   reliably follows only ~150–200 instructions before quality degrades and the harness's own system
   prompt already eats ~50 of that budget. Say which bar you're citing when you flag a file: "over
   Anthropic's 200" is a harder violation than "over this team's 100."
3. **Universal applicability only.** Every instruction must apply to *all* tasks in that file's
   scope. Task-specific guidance does not belong here. If it's conditional on file type or path
   (e.g. only matters when touching `src/api/**`), it belongs in a path-scoped file under
   `.claude/rules/` (see File Hierarchy & Scope), not a blanket rule in the root file — that's the
   harness's actual mechanism for "applies sometimes," not a workaround. If it's conditional on
   directory instead, it goes in that sub-directory's own context file. If it's a multi-step
   procedure, it goes in a skill.
4. **No linter's job.** Don't encode exhaustive code style, import ordering, or naming rules — LLMs
   are in-context learners and a linter/formatter enforces these better. Document the *non-obvious*
   only.
5. **Point, don't paste.** Reference `path/to/file.ts:42` instead of copying code blocks. Inlined
   snippets go stale and burn budget. Use progressive disclosure: link to a reference doc rather
   than inlining its content. Note `@path` imports don't save budget the way a reference doc does —
   an imported file is expanded and loaded at launch same as inline content, it only helps
   organization. Only a skill (loaded on demand) or a `.claude/rules/` path-scoped rule (loaded only
   when a matching file is touched) actually removes content from the default context load.
6. **No reactive hotfixes.** Don't add a rule to patch one isolated bad behavior you saw once.
   Context files are for durable, universal truths, not one-off corrections.
7. **Skip the obvious.** No generic wisdom ("write clean code", "handle errors"). If a competent
   dev or a capable model already knows it, leave it out.

## Structure: WHAT / WHY / HOW

Organize around three questions. Most root files need little more than this.

- **WHAT** — the project map: tech stack, top-level structure, key dependencies. Terse.
- **WHY** — purpose and context: what the app does, and the *why* behind non-obvious architectural
  decisions (so the model doesn't "fix" something intentional).
- **HOW** — working on it: exact build/test/lint/run commands (real ones — `pnpm`, `bun`, `make x`,
  not a generic `npm`), and any non-obvious workflow gotchas.

Add other sections *only* if they pass the Golden Rules (e.g. a genuinely non-obvious auth flow, a
domain-specific constraint). When in doubt, leave it out or push it to a reference file.

## File Hierarchy & Scope

| Scope | File | Holds |
|-------|------|-------|
| User-wide (all projects) | `~/.claude/CLAUDE.md` | Personal cross-project defaults |
| Project root (shared) | `./CLAUDE.md` or `./AGENTS.md` | Primary project context |
| Personal/local | `./CLAUDE.local.md` | Per-user prefs (gitignore it) |
| Sub-directory / package | `./<dir>/CLAUDE.md` or `AGENTS.md` | Context scoped to that dir only |
| Topic, always-on | `.claude/rules/<topic>.md` | One concern per file (testing, security, …); same load priority as root CLAUDE.md |
| Topic, path-scoped | `.claude/rules/<topic>.md` with `paths:` frontmatter | Loads only when Claude touches a matching glob — the mechanism for "applies sometimes" |

A directory's context file inherits the root — don't repeat the root's content. A monorepo package
file should hold only what's true for *that* package.

**`.claude/rules/` vs a sub-directory context file**: pick by what the content is conditional *on*.
Content that's true for every file under a directory → that directory's `CLAUDE.md`/`AGENTS.md`.
Content that's true for a file *type* or pattern regardless of where it lives (e.g. "every
`*.test.ts` file must…") → a `.claude/rules/` file with `paths:` frontmatter. This is the harness's
answer to "the root file is at budget but this instruction is real" — move it to a scoped rule
instead of loosening the budget or leaving it in root for tasks that never need it.

> Note: some repos use `CLAUDE.md` as a thin pointer (`@AGENTS.md`) so both Claude and other agents
> share one source of truth. Respect whichever convention the repo already uses; don't fragment it.

## Workflow

### 1. Discover

Find every context file in scope before changing anything:

```bash
find . \( -name "CLAUDE.md" -o -name "AGENTS.md" -o -name "CLAUDE.local.md" \) -not -path '*/node_modules/*' 2>/dev/null | head -50
find . -path '*/.claude/rules/*.md' -not -path '*/node_modules/*' 2>/dev/null
```

### 2. Audit against the rules

Read each file in full, then score it with the rubric in
[references/quality-rubric.md](references/quality-rubric.md). For each file note:

- **Line count** vs. the budget (flag anything over ~100; treat 100–200 as "over this team's bar,
  still under Anthropic's" and say so explicitly rather than calling it a hard violation).
- **Violations** of the Golden Rules — especially #2 (too long), #3 (task-specific or path-specific
  bleed-in that belongs in a `.claude/rules/` file instead), #4 (linter's-job content), #5 (inlined
  snippets, or content wrongly assumed to be "free" because it's behind an `@import`).
- **Staleness** — commands that would fail, paths/versions that no longer exist (verify against the
  actual repo, don't trust the file).

### 3. Report before editing

Always present findings *before* touching files. Keep it scannable: per file, give a grade, the line
count, the top violations, and a concrete "cut this / move this / keep this" list. Name *where* cut
content should go (a reference doc, a skill, a sub-dir file, a `.claude/rules/` path-scoped file, or
the linter config).

### 4. Edit with approval

After the user approves, apply changes. Show the intent of each cut/move. Preserve the repo's
existing conventions and headings where they're fine — surgical edits over rewrites, unless the file
is far enough gone that a rewrite is genuinely cleaner (say so and confirm).

## Anti-Patterns to Cut on Sight

- Exhaustive import-order / naming / formatting rules → delete; that's the linter's job.
- Long inlined code blocks (example configs, full snippets) → replace with a `file:line` pointer or
  move to a reference doc.
- Task-specific or feature-specific instructions in a root file → move to the relevant sub-scope.
- File-type or path-conditional instructions ("for every `*.tsx` file…") sitting in the root file
  or a directory `CLAUDE.md` → move to a `.claude/rules/` file with `paths:` frontmatter so it only
  loads when relevant, instead of always-on.
- Generic best practices and obvious advice → delete.
- Duplicated content across multiple context files → keep it in one place, let inheritance do the rest.
- One-off "hotfix" rules → delete unless they're genuinely universal.
- Content moved into an `@import` and counted as "saved" → it isn't; imports still load at launch.
  Only cutting it or moving it to a skill / path-scoped rule actually reduces the load.
