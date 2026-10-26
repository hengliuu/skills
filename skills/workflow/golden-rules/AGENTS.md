# Golden Rules

Team working style for AI coding harnesses. Applies to every session.
A project `AGENTS.md`/`CLAUDE.md` overrides these where they conflict.

## Code work

Invoke `karpathy-guidelines` before writing, reviewing, or refactoring code — it
carries the reasoning behind each rule. Trivial edits don't need it.

Comment only what the code cannot say: a why, a constraint, a non-obvious consequence.
A comment restating the line below it is noise the reader still has to check against the
code, so it costs attention twice. `karpathy-guidelines` carries the test.

Verification is part of the task, not a step after it. Work is done when its success
criterion has been checked and you can say what you ran. "Should work" is not done;
report failures with their output.

## Review — this is where the bottleneck is

Generation is cheap; review costs human time, so spend the effort there. Dispatch the
`reviewer` role (`role-reviewer`) before declaring work done, or invoke `requesting-code-review`
on a harness without subagents, and `receiving-code-review` when
findings come back — fix it or argue it, never silently drop it. Review against the
project's own standard, its `AGENTS.md` and any stack skills it names, rather than generic taste.

## Commits

Offer the `commit-group` skill whenever changes are ready — we want grouped, atomic
commits reviewed before execution, so never commit inline unless told to. Push is
always the user's manual step. No `Co-Authored-By` trailers; the git user is the sole
author.

## Starting a piece of work, or handing off a finished stage

Invoke `workflow-map` when the next step isn't obvious. It holds the stage-to-skill
table, the execution-tier decision, and where a spec, an architecture or a plan you
already hold actually lands — one map, instead of firing workflow skills to see which
fits.

When a plan is approved, invoke `workflow-map` before any execution: it reads the plan's task
table and picks how the work runs. Every plan ends in that table (task, depends on, files,
role, effort, check).

Work that arrived from someone else starts at `intent-capture`, not `brainstorming`:
the first records why anyone wanted this, the second decides how to build it, and only
the first survives the requester leaving.

## While a plan file exists

**The plan file on disk is the source of truth for progress.** Upstream
`writing-plans` / `executing-plans` only write to ephemeral TodoWrite, so nothing
records progress unless you do. Tick a task the moment it is verified, before starting
the next — a session that dies mid-plan must leave a file that tells the truth.
`workflow-map` carries the frontmatter fields.

## Any session with agent teams enabled

A subagent spawned **with a `name`** launches as a full teammate, not a one-shot
worker — a separate Claude at several times the cost, and it happens during ordinary
delegation you never framed as team work
([docs](https://code.claude.com/docs/en/agent-teams#how-claude-starts-agent-teams)).
Dispatch without a `name` unless a team is genuinely intended.

## Delegating to subagents

A fork always runs on the session's model, so a mechanical task sent as a fork
pays top-model prices for nothing. Fork only when the task needs this conversation's
context. Otherwise dispatch a `role-orchestrator` role with a full brief and the model and
effort from the `role-orchestrator` model map: chore on haiku, worker on sonnet, designer
and reviewer on opus. Name the role, model and effort in the reply each time you dispatch.

## Codebase map (project work)

Read the codebase map before exploring by hand, and treat codebase questions as graph
queries. Either map counts — `graft/` or `graphify-out/`. Never bulk-read a codebase;
when there is no map, aim Grep at the directories the task actually touches.
`workflow-map` covers the commands, and when to build, refresh, or install one.

## Autonomous runs

Invoke `loop-discipline` before setting any `/goal` or `/loop`. A loop without a hard
cap and a stall exit is banned.
