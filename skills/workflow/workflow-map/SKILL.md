---
name: workflow-map
description: >
  The map of how a piece of work travels from request to merged commit, and which
  skill owns each stage. Invoke it when you are about to start something and the path
  isn't obvious, when a stage just finished and you need the handoff, or when you have
  a spec, an architecture, a plan or a set of review findings already in hand and need
  to know where that lands. Triggers on "mulai dari mana", "gimana alurnya", "next
  step apa", "ini lanjut ke apa", a client or stakeholder request arriving, or any
  question about which skill to use for a stage. Consult it instead of firing several
  workflow skills and seeing which fits.
---

# Workflow map

Work travels through stages, each committing an artifact the next one can read. This
skill answers two things: **which stage you are actually at**, and **which skill owns
the next one**.

It does not do the work. It routes, then gets out of the way.

## What each stage buys

Read this before deciding anything. A stage that has nothing to protect on this
particular task is a stage that costs you and returns nothing — and the shape of the
work, not a rule, is what tells you which those are.

| Stage | What it buys you |
| --- | --- |
| **Intent** | An answer to "why was this built at all" that survives after the person who asked has moved on. Only worth buying when someone other than you asked. |
| **Design** | A decision made deliberately instead of by accident, and written down where it can be argued with. |
| **Plan** | Your place in the work, kept on disk, so a session dying mid-task costs minutes rather than the whole thread. |
| **Tier choice** | Parallelism you actually use, instead of paying for teammates that wait on each other. |
| **Review** | Defects found before someone else finds them, judged against the team's standard rather than taste. |

A one-line fix whose cause you already know has nothing on that list to buy. The project's
own conventions are the whole path, and
`systematic-debugging` joins it only when the cause is still unknown.

## Enter where you actually are

Stages run in order, but you rarely start at the beginning. Find the row that matches
what is already in your hands.

| What you have | Next | Produces |
| --- | --- | --- |
| A request from someone else — client, stakeholder, MoM, an incident | `intent-capture` | `intent/*.md`, then return here |
| An idea, nothing written down | `brainstorming` | a design, and a spec if the work is architectural |
| An FSD, URS or PRD (from the client or a product owner) | treat it as an architecture you already have, row below | a spec only for the parts the document leaves open |
| An architecture or design you already made | validate it against the codebase, then `writing-plans` | a plan |
| A spec, freshly written | `grill-me` | the same spec, with its weak decisions found |
| A spec that has been approved | `writing-plans`, ending in the [task table](references/task-table.md) | a plan |
| A plan that has been approved | pick a tier, below, from its task table | working code |
| Code finished, nobody has looked at it | `requesting-code-review` | findings |
| A worker's branch waiting for a human | `requesting-code-review` by the human | approve, or a repair |
| Review findings in hand | `receiving-code-review` | fixes, or a reasoned rebuttal |
| Work verified, nothing committed | `commit-group` | atomic commits |
| None of these rows | ask the user what they have | — |

Picking the row is a [decision point](#decision-points). The evidence is what is on disk
(`intent/`, the spec, the plan and its `status:`), not how the request was phrased. "Just
build X" with an approved plan already sitting in `docs/superpowers/plans/` is the
approved-plan row. Two rows that both fit usually means two pieces of work. Say that
instead of picking one.

### An entry point is a claim, not a fact

When someone arrives with an architecture already drawn — a tech lead who has done the
thinking — the useful move is to accept the entry point *and check it*, in that order.
Read the parts of the codebase it touches and confirm the design still holds there.

If it holds, go to `writing-plans` and don't redo the thinking. If part of it doesn't
survive contact, take **that part** back to `brainstorming` and leave the rest standing.
Planning around a design that quietly stopped being true is more expensive than the
check, and starting over insults work that was mostly right.

## Picking an execution tier

The shape of the work picks the tier. The wrong pick costs tokens and returns nothing.
This is a [decision point](#decision-points) too. The evidence is the plan's
[task table](references/task-table.md): which tasks depend on which, and which write the
same files. A plan without the table gets one first, then the tier is read off it. If the
table still doesn't say enough to tell, the answer is solo. Record the pick as `tier:` in
the plan frontmatter.

| The plan's tasks | Tier | Runs on |
| --- | --- | --- |
| Sequential, or share files | `executing-plans` (solo) | any harness |
| Parallel, results just return to you | `subagent-driven-development` | any harness with subagents |
| Parallel fan-out → verify, deterministic, must survive `/resume` | the `Workflow` tool | Claude Code only |
| Not one plan but a batch of independent tasks, each its own worktree and branch, merged by the lead | `role-orchestrator` | any harness with subagents |

Subagents are widely supported. On a harness without the `Workflow` tool that row simply
doesn't exist, and the rows around it still do: route parallel work to
`subagent-driven-development`. Parallel work that spans domains, each with its own files
and branch, goes to `role-orchestrator`.

## Decision points

A decision point is a routing call with a closed set of answers, made at a known step
in the work: which row above, which tier, what type a ticket is, which commit group a
file belongs to, which domain owns a task. Writing these down as typed decisions is what
keeps the path through the work from being improvised differently in every session.

Every decision point has four parts, and a skill that owns one lists them:

| Part | What it means |
| --- | --- |
| **Options** | A closed set, each with a one-line meaning. The options don't overlap, and together they cover every case. Include "none of these" when an input can fit nothing. |
| **Evidence** | What must be read before choosing: the files, the diff, the plan. Cite it only for an unsure pick. A sure pick needs no justification in the reply, because the explanation costs the reader more than it tells them. |
| **Confidence** | **Sure**: one option clearly fits the evidence. **Unsure**: two fit, or the evidence is missing. An unsure pick is shown as unsure, with the two candidates, and never resolved silently. |
| **Authority** | **Reversible** (routing to a stage, drafting): proceed on a sure pick. **Consequential** (commits, tickets, spawning a team, closing a plan): a human approves, however sure the pick is. |

The model proposes and the human authorizes anything consequential. Confidence decides
when to ask about the rest. A pick that turns out wrong is cheap to redo when it was
reversible. An unsure pick that was hidden turns into rework that nobody can trace back.

The options are written as an option → meaning table so that anything choosing between
them, the model or an external classifier, reads the same menu.

## When a stage stops

A stage that isn't converging costs more every turn it continues. These are the exits.
Each one hands the decision back to a human instead of looping:

| Stage | Stop and escalate when | Hand back |
| --- | --- | --- |
| Intent | The success measure can't be stated, or the requester can't be asked | The open questions, not a guessed intent |
| Design | The same decision is still open after two rounds of `grill-me` | That decision, as options with trade-offs |
| Plan | A task can't be given a checkable result | That part, back to design. The rest of the plan stands |
| Execution | A task fails verification three times, or an assumption in the plan proves false | The failure evidence, and the plan change it implies (`systematic-debugging` if the cause is unknown) |
| Review | The same finding comes back after two fix rounds | The finding, and why the fixes didn't hold |
| Any loop | `loop-discipline`'s cap or stall exit fires | What the loop achieved, and why it stalled |

Stopping is not failing. Keeping going past these points makes the eventual escalation
more expensive and harder to read.

## What this skill does not decide

`brainstorming` classifies design depth itself — spike, bounded, or architectural — and
only architectural work writes a spec file. Route to it and let it make that call; two
classifiers competing over the same decision is worse than either alone.

Same for the stack skills: they own what correct code looks like here. This map only
says when it is their turn.

## Tracking a plan

The plan file on disk is the source of truth for progress — `golden-rules` carries that
invariant because it has to hold even in a session that never reaches this skill. The
mechanics live here:

- Frontmatter: `status:` (`PENDING` → `IN_PROGRESS` → `DONE`), `created_by:` (set once),
  `current_handler:` (who is holding it now — a signal, not a lock), `tier:` (the
  execution tier that ran it — set when execution starts, so finished plans show which
  tiers paid off). Flip to `IN_PROGRESS` when execution starts, not after the first
  task lands.
- Boxes unticked but the work confirmed in git is stale bookkeeping, not unstarted
  work. Fix the file; don't redo the work.

## Handing context to workers that don't inherit the conversation

Subagents start with none of this conversation. A knowledge graph
is the cheapest way to give them the codebase, which is why the map matters more the
more the work fans out.

We support two, and the rule is the same for both: read whichever map is on disk, and
never propose a second one on top of it.

| Map | Build | Query | Refresh |
|---|---|---|---|
| `graft/` | `graft build` | `graft ask`, `graft callers`, `graft skeleton` | automatic, on every query |
| `graphify-out/` | `graphify .` | `graphify query "<q>"` | `--update`, or `--watch` |

- No map, and the work is more than a one-file change: offer to build one and let the
  user decide. Don't gate the work on it. Both extract code with tree-sitter, not a
  model, so the structural pass costs no tokens and the only real cost is wall-clock.
- The LLM layer is opt-in in both, and it is the only part that bills: `graft build
  --deep` for file summaries, graphify's INFERRED edges and report. Offer it when the
  user wants prose over structure, not by default.
- Neither is mature. Both are 0.x and ship weekly, so check which one the repo has
  instead of assuming a command exists, and don't hard-code flags into a plan.
- **Division of labour: code goes to graft, everything else goes to graphify.** Measured
  on a Python + TypeScript monorepo, not assumed. Graft answered an orientation question
  in 430 tokens against graphify's 1,534, ranked and carrying signatures, where graphify
  returned an unranked dump truncated by its own budget. Asked who calls a symbol,
  graphify answered a different question entirely.
- Docs, papers, SQL schemas, configs and images are graphify's alone. Graft indexes code
  only and silently skips every file type it doesn't parse, so it reports nothing rather
  than reporting a gap.
- **A default, not a ban.** Graphify reads code too, and remains the fallback where graft
  is blind: a language outside its 23, or a call bound through a class name
  (`Mapper.to_entity()`), which graft drops rather than guesses. Two caveats on the
  measurement — one repo, and no Go was tested.
- `graft callers` is trustworthy on module-level functions (49 of 49 on one, beating raw
  grep, which counted a comment). It is blind to class-bound calls, which is how mapper
  and repository layers are usually written. Never conclude "nothing calls this" from a
  zero: graft prints a warning saying the count may be short, and `graft grep` is the
  fallback it points at. Read the warning, not the zero.
- Neither installed: the need doesn't go away, only the tool. On a large codebase, or
  whenever the work feeds workers, say it's missing and offer the install — repeated
  Grep sweeps cost more context than one map, and their results don't transfer to
  workers at all.

## And at the end

Push is always manual, after your own review. `commit-group` groups the diff first.

## Closing the loop

Production is a source of work, not the end of it. An incident, an SLO breach, a metric
that crossed the threshold an intent's success measure named, or a client complaint is
new work, and it enters at `intent-capture` the same way a meeting does. Patching it
silently is what turns the loop back into a waterfall: the next person finds a change
with no record of what forced it.

Check a shipped intent's success measure on the date it names. Hitting it closes the
intent. Missing it is itself a new intent, and the number to put in it is already
written down.
