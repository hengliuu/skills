# How work flows

How a piece of work travels from someone asking for it to something merged. The
skills and golden rules in this repo are built around this path — each stage is
useful on its own, but this is the shape they assume.

The structure follows Anthropic's
[AI-native SDLC playbook](https://claude.com/blog/the-ai-native-sdlc-playbook).
Its central claim is worth stating up front, because it explains every choice below:
**code is no longer the bottleneck.** Generation got cheap; review and approval still
run at human speed. So the work is organised to protect human attention, not to
produce code faster.

## The shape

Every stage commits an artifact the next stage can read. That chain — intent, spec,
plan, diff, review findings — is the audit trail. Nothing here lives in a chat log.

```
  ┌────────────┐
  │  1. PLAN   │   requester tells the story  ──▶  Claude writes it up
  └─────┬──────┘
        │  commit ▸ intent/YYYY-MM-DD-<topic>.md
        │           problem · outcome · measure · affected · constraints · risks · open Q
        ▼
   ◆ GATE ── requester: "this is what I asked for"   (Status: draft → accepted)
        │
        ▼
  ┌────────────┐
  │ 2. DESIGN  │   requirements and design collapse into one session
  └─────┬──────┘
        │  commit ▸ docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
        │           or docs/designs/<feature>.md for a large feature (EGM)
        ▼
   ◆ GATE ── requester approves the spec; policy concerns go to their owners
        │
        ▼
  ┌────────────┐
  │  3. BUILD  │   plan mode first (read-only), then implementation
  └─────┬──────┘
        │  commit ▸ docs/superpowers/plans/YYYY-MM-DD-<feature>.md
        │           + AGENTS.md / CLAUDE.md  ← institutional knowledge
        ▼
   ◆ GATE ── engineer iterates the plan before a line of code is written
        │
        ▼
  ┌────────────┐
  │  4. TEST   │   continuous feedback loops, not a gate at the end
  └─────┬──────┘
        │  commit ▸ verified output — Claude checks before a human looks
        ▼
  ┌────────────┐
  │ 5. DEPLOY  │   Claude reviews and ranks findings by severity
  └─────┬──────┘
        │  commit ▸ diff + PR + review findings
        ▼
   ◆ GATE ── code owner approves the PR
   ◆ GATE ── release: a hook exiting 2 holds the action until approval
        │
        ▼
  ┌─────────────┐
  │ 6. MAINTAIN │   monitoring and incidents produce a NEW intent.md
  └─────┬───────┘
        │
        └──────────────────────▶  back to stage 1
```

```
   intent  ──▶  spec  ──▶  plan  ──▶  diff  ──▶  review findings
  "asked"     "decided"   "doing"   "changed"     "checked"
     └──────────── all in git, ordered, dated ───────────┘
```

## What runs each stage

`workflow-map` is the router across all of this: it holds the stage-to-skill table
and the tier decision, and it is the thing to invoke when the next step isn't obvious.
This document is the explanation for people; that skill is what an agent reads.

Two things in it matter to people, not only to agents:

- **Decision points.** Routing calls with a fixed menu, such as which stage, which tier,
  a ticket's type, a file's commit group, or a task's domain. Each one names its options
  and its evidence. An unsure pick is shown to you with both candidates instead of being
  resolved quietly. Anything consequential (commits, tickets, spawning a team, closing a
  plan) waits for your approval, however confident the pick.
- **Stop conditions.** Each stage has a point where it stops and hands the decision back
  to you instead of looping, for example a design decision still open after two grill
  rounds, or a task that fails verification three times.

| Stage | Artifact | What we use |
| --- | --- | --- |
| 1 Plan | `intent/` | `intent-capture` |
| 2 Design | spec | `brainstorming`, then `grill-me` on the spec before approving it. A large feature goes through EGM instead: `egm-brainstorm`, `egm-draft`, `egm-review`, `egm-resolve` |
| 3 Build | plan | `writing-plans`; plan status written back to the file; the project's own conventions carry the standard. On the EGM path, the approved design doc plus a task table is the plan |
| 4 Test | verified output | `test-driven-development`, `verification-before-completion` |
| 5 Deploy | diff, PR, findings | `role-reviewer`, `receiving-code-review`, `/commit-group` |
| 6 Maintain | a new intent | `intent-capture` again, and `egm-drift-report` weekly where EGM design docs exist |

Third-party skills in that table install separately. See the install guide's
[Recommended community skills](docs/install.md#recommended-community-skills).

## Stage 1 — Plan

Skip this when the requester and the implementer are the same person; a bugfix does
not need an intent file. It earns its keep when someone else is asking, because that
is where "I never asked for that" costs money.

The rule is that an intent records the ask, not the answer — no technology, no screens,
no vendors. `intent-capture` runs the interview, because the four things that make an
intent useful (impact stated as a number, constraints, risks, unresolved questions) are
the four things requesters never volunteer.

The impact number carries a source and a date, which makes it a **success measure**.
That single field is what stage 6 has to read; without it the return arrow is a drawing.

## Stage 2 — Design

`brainstorming` classifies the work first — spike, bounded, or architectural — and only
architectural work produces a spec file. Take the heavier path when in doubt; the
classification ratchets one way.

Then **run `grill-me` on the finished spec before approving it.** `brainstorming`'s own
step 7 is a self-review, and a model that just wrote a document is poor at auditing it —
it checks for placeholders and contradictions, never for whether a decision was right.
An adversarial pass is what catches that.

A large feature, one that is costly to get wrong, takes the EGM path instead. EGM (the
[Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model)) drafts one
design doc that holds the spec and its build steps, then has zero-context subagents review
it from several angles: simplicity, a newcomer's reading, design and scale, and whether a
model could build it without guessing. That review is the adversarial pass, done by
reviewers who never saw the conversation. It costs several subagent runs per feature, so
smaller work stays on `brainstorming`. `workflow-map` makes the size call. EGM's skills
start only when you run them, so on this path the agent tells you which one is next.

## Stage 3 — Build

**The plan file on disk is the source of truth for progress.** Upstream
`writing-plans` / `executing-plans` only write to ephemeral TodoWrite, so a plan is
ticked task by task in the file itself, as each task is verified — never batched at the
end. A session that dies mid-plan must leave a file that tells the truth.

### Picking an execution tier

Four tiers, from a solo run to a batch of worktrees, and the shape of the work picks which.
The table lives in `workflow-map` rather than here, so there is one copy to keep
true — invoke it when a plan is approved and it will make the call.

## Stage 5 — Deploy

This is where the bottleneck actually is, so it gets the attention that used to go into
writing code faster.

- The `reviewer` role (`role-reviewer`) before declaring work done, not after.
- `receiving-code-review` when findings land: fix it or argue it, never silently drop it.
- Review against **the project's own conventions**: its `AGENTS.md` and any stack skills it
  names. That is the standard, and generic taste is not.
- `/commit-group` groups the diff into atomic commits for review before anything runs.
  Push stays manual, always.

## Where we are

```
   1 ~ ──▶ 2 ✓ ──▶ 3 ✓✓ ──▶ 4 ~ ──▶ 5 ✓ ──▶ 6 ~
```

Stages 2–3 are stronger than the playbook prescribes — nothing upstream writes plan
status back to disk. The two ends are still the thin parts, but they now reach each
other: an intent carries a success measure with a date, and `workflow-map` routes a
breach of it back to stage 1. What holds that together is a rule, not a mechanism.

Open, in order of what unblocks what:

- **Stage 6 has a rule and nothing that notices.** An incident, a breached SLO, or a
  missed success measure is routed back to `intent-capture`. Nothing watches, though:
  no alert opens the file and no date pulls the measure, so the loop closes only when
  a person remembers to close it. `egm-drift-report` covers one slice of this, code that
  drifted from its design doc, but only when someone runs it.
- **`REVIEW.md`** — a review policy as an artifact (which passes run, severity levels,
  what to skip). Cheapest thing left on this list.
- **Deploy gates** — the playbook uses a hook exiting 2 to hold a release until an
  approval token exists. We do not use that pattern here.
