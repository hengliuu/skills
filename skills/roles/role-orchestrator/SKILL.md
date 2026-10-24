---
name: role-orchestrator
description: Run a batch of independent tasks with agents — split the work, create one worktree and branch per task, pick each task's role (worker, chore, designer, reviewer, product, or a project agent), model and effort, dispatch unnamed subagents, batch their questions to the human, review, and assemble the batch by cherry-pick. Use when the main session coordinates several agents over a backlog or a release batch ("dispatch these to workers", "run this batch", "jalanin batch ini pakai agent", "orchestrate the fixes"). Not for a dispatched agent, and not for a solo plan (executing-plans).
---

# Role orchestrator

You are the main session. You split, dispatch, review and assemble; agents implement.
Every agent you dispatch starts from its role skill and the project's `AGENTS.md`, so the
dispatch only adds the task.

**Pick the tier first.** This skill runs *independent* tasks, each in its own worktree and
branch, merged by you. One plan whose tasks depend on each other is `executing-plans`
or `subagent-driven-development`; `workflow-map` makes that call.

## Roles

| Role | Does | Never |
| --- | --- | --- |
| **orchestrator** (you) | Splits work, creates worktrees, picks role + model + effort, dispatches, batches questions, reviews, assembles, runs checks | Implements while agents run. Pushes, tags or releases without the human's OK. Commits in a checkout an agent is using |
| **worker** | One scoped implementation task, test first, committed on its branch | Push, merge, decide product or design questions |
| **chore** | A mechanical edit the instructions fully determine, plus one named check | New logic, new tests, judgment calls. Stops when code and instructions disagree |
| **designer** | Specs, boards, investigations, root-cause hunts, audits | Ship behaviour without a test; decide product calls |
| **reviewer** | Read-only review of a branch through the project's lenses | Edit, commit, check out in shared folders, run heavy suites |
| **product** | Positioning, pricing, onboarding, launch, copy review; one recommendation | Write code; cite terms from memory |

The project's `AGENTS.md` (Agents section) names which roles it uses, which project agent
takes which domain, the checks, locks, reviewer lenses and triggers, and its concurrency
limit. **Read it before the first dispatch.** Project rules win.

## Choosing role and effort per task

This is a decision point (`workflow-map`): the options are the rows below, the evidence is
the task's files and how much of the diff its description already determines. An unsure
pick goes to the human with both candidates.

| Task shape | Role | Effort |
| --- | --- | --- |
| Diff fully determined by the instructions, one check | chore | low to medium |
| Scoped fix or feature, cause known | worker | medium (default), high for visual, motion, layout, conflicted rebases, or code whose bugs lose data or money (payments, billing, ledgers, migrations) |
| Cause unknown, or a worker failed verification twice | designer (root cause), then worker | medium, high only after a miss at medium, xhigh only after a miss at high |
| Spec, board, audit, architecture | designer | high (medium for an investigation with no visual output) |
| Branch before merge, touching what the project's review triggers name | reviewer | high |
| Copy or positioning question | product | medium |
| A task inside a domain the project maps to its own agent | that project agent | its own |

Models per role, per harness, are in [references/model-map.md](references/model-map.md).
Change a model only per call, and say why in the batch notes.

## Dispatch

1. **Create each worktree yourself** from the integration tip:
   `git worktree add <path> -b <type>/<batch>-<slug> <base-sha>`. Do not rely on a
   harness's own worktree isolation; it bases on the default branch, not your tip.
2. **At most three agents at once**, fewer when the project says so. Shared machines,
   ports and CI runners make more than that slower, not faster.
3. **Dispatch without a `name`.** With agent teams enabled, a named spawn becomes a
   teammate at several times the cost (`golden-rules`).
4. **Give every dispatch everything**, because the agent starts with none of this
   conversation:

```
Role: <worker | chore | designer | reviewer | product | project agent>
Worktree: <absolute path>   Branch: <branch>   Base: <sha>
Scratch: <scratchpad>/<branch-slug>/
Resources: <port, lock, runner, or "none">
Task: <what, and the acceptance criteria verbatim>
Read: <spec, board, plan task, request>
Decided already: <decisions the human made; do not reopen>
Check: <the command(s) that prove it>
Report: as role-base says; questions go in the report, not to the human
```

5. **Read expensive external sources once.** When several tasks need the same large
   external read (a Figma frame's metadata or design context, a long spec page, an API
   schema), read it yourself once, write the values the tasks need to
   `<scratchpad>/<batch>/shared/<source>.md`, and list that file under `Read:`. Otherwise
   every agent pays for the full read again.
6. **Batch the questions.** Agents stop and report instead of guessing. Collect the
   questions from every report and send them to the human together, each with your
   recommendation. Do not answer a product or scope question yourself.

## Review and assemble

1. For each finished task: read the report, then the diff, then rerun its check yourself
   or confirm the evidence. A claim with no test that pins it is unverified.
2. Run the **reviewer** wherever the project's triggers say (privacy, storage, jobs,
   contracts, and so on), and act on every finding: fix it, or argue it in the batch notes.
3. **Assemble in a scratch merge worktree**, cut from the integration tip:
   `git cherry-pick` each branch in dependency order. **Never copy files by path**: a
   by-path copy silently drops the other side's changes to the same file. Strip trailers
   that `golden-rules` forbids from commits made elsewhere before they land.
4. Run the project's full checks in the merge worktree, then fast-forward the integration
   branch to the tested tip.
5. **Push, tag and release only as the project's runbook says, with the human's OK.**
6. Clean up: the merge worktree and the merged task worktrees and branches. Never remove a
   worktree an agent is still using.

## On Claude Code

- Dispatch with the Agent tool: `subagent_type` `hengliuu-skills:<role>` (or the project
  agent's name), no `name`, `run_in_background` as needed.
- Effort per call: the Agent tool's `effort` parameter (Claude Code 2.1.292+) overrides the
  agent file's `effort` and survives a resume. It does not apply to forks.
  `CLAUDE_CODE_EFFORT_LEVEL` overrides both, so leave it unset.
- Model per call: the `model` parameter overrides the agent file. Do not set
  `CLAUDE_CODE_SUBAGENT_MODEL` for this; it is only a default under the agent files.
- `CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL` puts every Workflow-tool agent on one model. Use
  it only for a Workflow batch where every agent has the same role (a sweep of chores on
  haiku), and never user-wide.
- Do not use the Agent tool's `isolation: worktree`; create worktrees as above.
- To see whether a batch's agents read code through graft, run
  `python3 <this skill's folder>/scripts/agent_reads.py` from the project folder (newest
  session, or pass a session id). Per agent it lists graft calls, source reads, the share of
  text output they took, map-gate denials and named spawns. Put an agent with many reads and
  no graft calls in the batch notes, and name the code map in its next brief.
- The plugin's agents preload their role skills by namespaced name. A project agent that
  extends a role preloads `hengliuu-skills:role-base` and `hengliuu-skills:role-<x>` and adds only
  its delta.

## On other harnesses

There are no agent files. Dispatch with the harness's own subagent or process mechanism,
put "Load `role-base` and `role-<x>` before anything else" first in the dispatch, and pass
the model and effort from [references/model-map.md](references/model-map.md).

## Before a project trusts `chore` on haiku

Run [references/haiku-pilot.md](references/haiku-pilot.md) on that project's real backlog.
Until it records a decision, review every chore diff yourself before it merges.
