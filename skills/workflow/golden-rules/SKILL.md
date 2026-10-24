---
name: golden-rules
description: Carries the team's working-style rules as an AGENTS.md file so they travel with the skills CLI. Deliberately inert — it never triggers and has nothing to run; install it, then link its AGENTS.md into your harness's global context once.
disable-model-invocation: true
---

# Team working style

This folder exists to **deliver a file**, not to run a procedure. The file is
`AGENTS.md`, next to this one: the team's working style, and the single source of
truth for it.

Read it before linking it — it is short, and it is an instruction budget rather than a
manual. It covers how we handle code work, review, commits, plan files, agent teams,
codebase maps, and autonomous runs, and it points at skills for the mechanics rather
than repeating them.

## Why it ships as a skill

`npx skills add` installs skill folders whole — every file in them, refreshed by
`npx skills update`. Nothing else in this repo reaches a non-Claude-Code harness
automatically. Shipping the rules here is what lets them arrive, and keep arriving.

It is marked `disable-model-invocation`, so it never fires on its own. There is no
procedure to invoke.

That also means the usual advice about writing a description — make it eager, so the
skill is not missed — **inverts here.** The description's only reader is a person
scanning `npx skills list`. Keeping it plain is deliberate; making it sound like a
trigger would be a regression, not an optimization.

## How the rules actually reach a session

| Harness | How |
| --- | --- |
| Claude Code, via the plugin | Injected every session by the plugin's SessionStart hook. Nothing to do. |
| Everything else | Link this folder's `AGENTS.md` into the harness's global context, once. |

The second row is manual because no other harness has a hook engine to inject it.
**Link, don't paste.** `skills update` replaces this folder at the same path, so
an import or a symlink pointing at `~/.agents/skills/golden-rules/AGENTS.md`
keeps loading the current rules. A pasted copy goes stale silently. If you pasted anyway,
paste again whenever `skills update` names `golden-rules` in its output.

The exact file, command and known trap for each harness (opencode, Codex, Gemini CLI,
Antigravity, Kiro, Claude Code without the plugin) live in the playbook README, under
**Load the global context per harness**. They are kept in one place because a wrong
path fails silently: the file sits there and nothing reads it.

## What this is not

Not a replacement for a project's own `AGENTS.md`. A project file overrides these
rules where they conflict — that is stated in the rules themselves. For a new repo,
start from
<https://github.com/hengliuu/skills/blob/main/templates/project-level/AGENTS.md>.
