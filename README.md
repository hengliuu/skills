# skills

**Skills and hooks that make AI coding agents plan, verify and get reviewed before anything ships.**

[![CI](https://github.com/hengliuu/skills/actions/workflows/ci.yml/badge.svg)](https://github.com/hengliuu/skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Good skill collections teach an agent how to work. Under load it still edits before it
thinks, calls work done without running it, and merges what nobody reviewed. These skills
add the part that makes the habits stick: rules that load into every session on their own,
and hooks that stop the agent at the moments it most often cuts corners.

Generation is cheap. Review is where the time goes, so that is where this repo spends its
effort.

## What makes it different

1. **Rules that load themselves.** A short rule file, the
   [Golden Rules](skills/workflow/golden-rules/AGENTS.md), is injected at session start. It
   tells the agent which skill to reach for at each moment, so you stop re-briefing it.
2. **Gates, not suggestions.** Hooks pause the first code edit of a session until the
   coding guidelines are loaded, and the first merge until a reviewer has run. Each gate
   fires once, so it is a stop to think, never a loop. The hooks have their own test suite.
3. **Roles with their own model and effort.** Six agents (worker, chore, designer,
   reviewer, product, project manager) each work in their own git worktree, on the model
   the job needs: mechanical edits on Haiku, implementation on Sonnet, design, review,
   product and tracker calls on Opus.
4. **One map from request to merge.** `workflow-map` routes each piece of work to the
   stage and skill that own it. Every plan ends in a task table (task, depends on, files,
   role, effort, check), so "done" always has a named check behind it.

## How work flows

```
request ──▶ intent ──▶ spec ──▶ plan ──▶ build ──▶ review ──▶ commit
              │         │        │         │          │          │
          intent.md  spec.md  plan.md   tests     findings   grouped commits
```

A human approves each handover, and pushing is always the human's step.
[WORKFLOW.md](WORKFLOW.md) walks through every stage.

## Install

On Claude Code. [superpowers](https://github.com/obra/superpowers) is required, since these
skills build on its planning, TDD and review skills.

```
npx skills@latest add obra/superpowers -a claude-code -g
/plugin marketplace add hengliuu/skills
/plugin install hengliuu-skills@hengliuu
```

Check it worked: open a new session and ask *"What do the Golden Rules say about
commits?"*. The answer should name `commit-group` and say pushing is manual. Skills appear
namespaced, for example `hengliuu-skills:workflow-map`.

> [!NOTE]
> The plugin runs hooks: a SessionStart hook that loads the rules, and PreToolUse gates on
> edits, merges and subagent dispatch. Read them in [`hooks/`](hooks) before you install.
> Start a session with `HENGLIUU_GATES=off` to turn the gates off.

opencode, Codex, Gemini CLI, Antigravity, Kiro and other harnesses install the same skills
with `npx skills@latest add hengliuu/skills`, plus one manual step for the rules.
See [docs/install.md](docs/install.md).

## What's inside

### [Workflow](skills/workflow)

| Skill | What it does |
|---|---|
| [`golden-rules`](skills/workflow/golden-rules/AGENTS.md) | The working-style rules. Loaded every session, never invoked |
| [`workflow-map`](skills/workflow/workflow-map/SKILL.md) | Routes work to the right stage and skill, and picks how an approved plan runs |
| [`intent-capture`](skills/workflow/intent-capture/SKILL.md) | Records why someone asked for the work before anyone decides how to build it |
| [`commit-group`](skills/workflow/commit-group/SKILL.md) | Groups changes into atomic commits and shows the plan before anything is committed |
| [`loop-discipline`](skills/workflow/loop-discipline/SKILL.md) | Hard caps and stall exits for `/goal` and `/loop`, so nothing runs unattended without a limit |

### [Engineering](skills/engineering)

| Skill | What it does |
|---|---|
| [`karpathy-guidelines`](skills/engineering/karpathy-guidelines/SKILL.md) | Surface assumptions, write the minimum, keep the diff surgical, name the check |
| [`claude-md-author`](skills/engineering/claude-md-author/SKILL.md) | Writes and slims `AGENTS.md` and `CLAUDE.md` so every line earns its place |

### [Roles](skills/roles)

| Skill | What it does |
|---|---|
| [`role-orchestrator`](skills/roles/role-orchestrator/SKILL.md) | Splits a batch into tasks, one worktree each, picks each task's role, reviews and assembles |
| [`role-worker`](skills/roles/role-worker/SKILL.md) | One scoped implementation task, test first, committed on its own branch |
| [`role-chore`](skills/roles/role-chore/SKILL.md) | A mechanical edit the instructions fully determine, plus one named check |
| [`role-designer`](skills/roles/role-designer/SKILL.md) | Specs, investigations and root-cause hunts, delivered as documents |
| [`role-reviewer`](skills/roles/role-reviewer/SKILL.md) | Reviews a branch with severity, file and line, a failure scenario and the smallest fix |
| [`role-product`](skills/roles/role-product/SKILL.md) | Positioning, pricing, onboarding and copy review, one recommendation with its reason |
| [`role-project-manager`](skills/roles/role-project-manager/SKILL.md) | Tracker structure and sync: story per requirement, states by group, Definition of Done, status from evidence |
| [`role-base`](skills/roles/role-base/SKILL.md) | The contract every dispatched role shares |

On Claude Code, six thin agents in [`agents/`](agents) preload these skills and set each
role's model and effort.

### What it leaves to you

There is no opinion here on your stack. How you write React, Go or SQL belongs to your
team, so reviews check the work against your project's own `AGENTS.md` and whatever stack
skills you choose. These skills own the process around the code, not the code style.

## Layout

```
.claude-plugin/   marketplace and plugin manifests
skills/           workflow, engineering and roles, one folder per skill
agents/           the six role agents for Claude Code
hooks/            session-start rules, gates and their tests
templates/        a starter AGENTS.md for your own projects
```

## Builds on

This repo stands on other people's work, and says so.

- [superpowers](https://github.com/obra/superpowers) by Jesse Vincent: brainstorming,
  plans, TDD and code review. Required.
- [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) by
  forrestchang. `karpathy-guidelines` is a fork of it (MIT), and also draws on
  [Andrej Karpathy's notes](https://x.com/karpathy/status/2015883857489522876), read directly.
- [Matt Pocock's skills](https://github.com/mattpocock/skills). `grill-me` is the
  recommended way to stress-test a spec before it becomes a plan.

Third-party skills are never copied into this repo. The plugin checks for what it needs at
session start and tells you what to install. The full list is in
[Recommended community skills](docs/install.md#recommended-community-skills).

## Contributing

Issues and pull requests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

[MIT](LICENSE). Built by [Hengky](https://github.com/hengliuu).
