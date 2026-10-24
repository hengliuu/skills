# Roles

Portable agent roles for one way of working: a main session (the orchestrator) runs a batch of independent tasks with unnamed subagents, one worktree and branch each, and assembles the batch by cherry-pick.

Role behaviour lives in skills, so it travels to any harness through the skills CLI. On Claude Code, five thin agents in [`agents/`](../../agents) preload those skills and set each role's model and effort. The role skills set `user-invocable: false` and say in their descriptions that they load only when dispatched, so an ordinary session does not pick them up.

| Skill | What it does |
| --- | --- |
| [role-orchestrator](role-orchestrator/SKILL.md) | Gives the main session its method: task-to-role table, dispatch, review, assembly by cherry-pick and the per-harness model map. |
| [role-base](role-base/SKILL.md) | Sets the contract that worker, chore and designer share: work only in the worktree, keep scratch tidy, stop and report, write the final report. |
| [role-worker](role-worker/SKILL.md) | Does one scoped implementation task, test first. |
| [role-chore](role-chore/SKILL.md) | Applies a mechanical edit the instructions fully determine, and stops on any mismatch. |
| [role-designer](role-designer/SKILL.md) | Writes specs, boards, investigations, root-cause hunts and audits. |
| [role-reviewer](role-reviewer/SKILL.md) | Reviews one branch read-only through the project's lenses, or generic ones when it names none. |
| [role-product](role-product/SKILL.md) | Answers positioning, pricing, onboarding and launch questions and reviews copy that workers invented. |

## Agents (Claude Code only)

| Agent | Model | Effort | Preloads |
| --- | --- | --- | --- |
| `hengliuu-skills:worker` | sonnet | medium | `role-base`, `role-worker`, `karpathy-guidelines` |
| `hengliuu-skills:chore` | haiku | medium | `role-base`, `role-chore`, `karpathy-guidelines` |
| `hengliuu-skills:designer` | opus | high | `role-base`, `role-designer`, `karpathy-guidelines` |
| `hengliuu-skills:reviewer` | opus | high | `role-reviewer`, `karpathy-guidelines`, with tools limited to `Read, Grep, Glob, Bash, Skill` |
| `hengliuu-skills:product` | opus | medium | `role-product` |

The reviewer is read-only by instruction. It has Bash, so the role skill tells it to change nothing.

The [model map](role-orchestrator/references/model-map.md) is the single source for these values, and a unit test fails when an agent file drifts from it.

The chore agent runs on Haiku by default. A project confirms that with its own [Haiku pilot](role-orchestrator/references/haiku-pilot.md), and the orchestrator reviews every chore diff until it has. If the pilot misses, set the agent to `sonnet` in a project agent that extends `chore`, or in the dispatch's per-call `model`.

## Plugging in a project

1. Install the plugin at user scope. Plugin agents work in every folder, unlike a project's `.claude/agents/`, which loads only in the folder the session started in.
2. Add an `## Agents` section to the project's `AGENTS.md`. The starter [`templates/project-level/AGENTS.md`](../../templates/project-level/AGENTS.md) has one: roles in use, project agents per domain, checks, locks, reviewer lenses and triggers, the concurrency limit, and a raised effort such as worker `high`.
3. Let a project agent extend a role instead of shadowing it. It preloads `hengliuu-skills:role-base`, `hengliuu-skills:role-worker` and `hengliuu-skills:karpathy-guidelines` by their namespaced names (a bare name can resolve to a project skill of the same name first) and adds only its delta, such as the stack skill.

## Hook

Before an Agent call to a role or a project agent, `hooks/dispatch_check.py` adds two notes to the context and never blocks. The model check fires once per role per session when the dispatch passes a `model` that differs from the agent file. The tier check fires once per session when `workflow-map` has not run. `HENGLIUU_GATES=off` silences both.

## Requires

Claude Code 2.1.296 or later, because the agents use `autoCompactWindow`. Also [superpowers](https://github.com/obra/superpowers), installed separately.

## Tests

```
python3 -m unittest discover -s skills/roles/role-orchestrator/tests
python3 -m unittest discover -s hooks/tests
```
