# Workflow

Skills that carry a piece of work from request to merged commit. They hold the Golden Rules, the map of which skill owns each stage, and the habits that keep an agent from drifting: capturing intent, committing in logical groups, and capping autonomous loops.

| Skill | What it does |
| --- | --- |
| [golden-rules](golden-rules/SKILL.md) | Carries the working-style rules as an `AGENTS.md` so they travel with the skills CLI, and never triggers by itself. |
| [workflow-map](workflow-map/SKILL.md) | Shows which stage you are at and which skill owns the next one, from request to merged commit. |
| [intent-capture](intent-capture/SKILL.md) | Records what a client or stakeholder asked for and why, before anything is designed. |
| [commit-group](commit-group/SKILL.md) | Groups a dirty working tree into atomic commits and shows the plan before it runs. |
| [loop-discipline](loop-discipline/SKILL.md) | Helps you write a `/goal` or `/loop` that has a cap and a way out when it stalls. |

## Hooks (Claude Code only)

At session start the plugin injects the Golden Rules and warns when superpowers is missing. It also warns when the repo has a build manifest but no codebase map.

Before a tool runs, `hooks/gate.py` stops two Golden Rules from being skipped. Each gate fires at most once per session, and a retry always passes, so it costs one turn and never loops.

| Gate | Fires on | Unless |
| --- | --- | --- |
| karpathy | The first write to a code file, by Edit, Write, NotebookEdit or a Bash command that writes one | `karpathy-guidelines` was invoked in the session |
| review | The first `git merge` or `git cherry-pick` that brings in a work branch | A reviewer agent or `requesting-code-review` ran in the session |

Subagents skip both gates. One more check runs for subagents only, on every call: an Agent call with a `name` is denied, because with agent teams on a named spawn becomes a teammate at several times the cost.

`hooks/map_gate.py` is the opposite case, for subagents only. It counts the lines of each source file an agent has printed into its context, and once that reaches 120 lines it denies the read and points to `graft skeleton`. After three denials of one file the read passes, so an agent never loops. It stays silent for the main session, for edits, for config and prose files, and in a repo with no graft index.

Set `HENGLIUU_GATES=off` in the environment to turn off every gate in an emergency. Every hook runs on Python 3.9, the `/usr/bin/python3` macOS ships.

Requires [superpowers](https://github.com/obra/superpowers), installed separately with `npx skills@latest add obra/superpowers -a claude-code -g`.
