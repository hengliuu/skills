# <Project Name>

> Starter AGENTS.md. Symlink `CLAUDE.md -> AGENTS.md` so every harness reads the same file:
> `ln -s AGENTS.md CLAUDE.md` (needs `git config core.symlinks true`; Windows: Developer Mode).
> Keep this file short — it loads every session. Details go in per-directory AGENTS.md files.
> `AGENTS.md.example` next to this file shows one filled in.

## What is this project?

<One paragraph: what it does, who it's for.>

## Repo map

- `<dir>/` — <what lives here>
- `<dir>/` — <what lives here>

## Working style - Skills

Working-style rules come from `golden-rules` — auto-injected each session
on Claude Code, linked into the harness's global context everywhere else.
Rules here override them for this repo only.

- **Type safety is the priority.** No `any`, no redundant or duplicate code.
- **New feature / behavior change → `workflow-map` first.** It picks the design path: `brainstorming`, or EGM for a large feature.
- **Stack skills:** <the pattern skills this repo follows, e.g. your team's React skill for `web/`.>
- Invoke skills proactively; the user shouldn't have to name them.

## Project-specific conventions

<e.g. shared module path (`<org>/shared` in the skills = `myproject/shared` here),
ports, package manager, i18n rules.>

## Agents

<Only if an orchestrator dispatches agents here (`role-orchestrator`, from the roles skills).
Delete this section otherwise. Longer rules go in a file named here.>

- **Roles used:** <worker, chore, designer, reviewer, product>. Project agents:
  <`<dir>/` → `<project-agent>`>.
- **Checks:** <command an agent runs before reporting>. Heavy runs: <lock or wait, or "none">.
- **Never touch:** <paths no agent may open or change>.
- **Reviewer lenses, in order:** <e.g. security, data loss, contracts, tests>. Review when
  a branch touches <triggers>.
- **Limits:** at most <3> agents at once. Raised defaults: <e.g. worker effort high>.
- **Release runbook:** <path, or "the orchestrator never releases">.

## Commands & gotchas

- `make dev` / `pnpm dev` — <how to run>
- `make test` — <how to test>
- Never commit secrets or read `.env` (only `.env.example`).

## End-of-session hygiene

When a task is complete and there are uncommitted changes, proactively offer
`/commit-group` to organize changes into atomic commits.
