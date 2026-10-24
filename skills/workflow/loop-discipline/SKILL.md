---
name: loop-discipline
description: Golden rules for autonomous execution — how to write a /goal condition that can actually terminate, when to use /loop instead, and the no-progress rule. Use whenever setting or reviewing a /goal or /loop, choosing between them, or when the user asks how to keep a session working autonomously without it running forever.
---

# Loop discipline — /goal and /loop safety

Why this exists: a real session once set a goal with no verifiable end state. It looped
for two days, pegging the GPU and draining the battery, before anyone noticed. Every
rule here traces back to preventing that class of failure: loops must have verifiable
feedback, layered exits, and no-progress detection.

## The DoD template — every /goal condition needs all four

The evaluator is a small model that reads only the conversation transcript. It cannot
run commands or read files. So the condition must be something the session's own output
can demonstrate.

1. **One measurable end state** — a test result, build exit code, file count, empty
   queue. "Refactor the auth module" is a process, not an end state; the evaluator can
   never say yes to it.
2. **A stated check** — how the session proves it, e.g. "`npm test` exits 0" or
   "`git status` is clean". Run the check so its output lands in the transcript.
3. **Constraints** — what must not change on the way, e.g. "no other test file is
   modified".
4. **A hard cap** — `or stop after N turns` / `or stop after 2 hours`. Non-negotiable:
   a goal without a cap must not be set. If the condition can't be met, the cap is the
   only thing standing between you and an unbounded loop.

Example of a complete condition:

```
/goal all tests in test/payments pass (`go test ./internal/payments/...` exits 0),
lint is clean, no files outside internal/payments and its tests are modified —
or stop after 20 turns
```

## Hard prohibitions

- **Never use /goal for monitoring, polling, or periodic work.** Those have no finish
  line; goal-based execution either loops forever or stops too early. Use `/loop` with
  explicit exits, or a scheduled task.
- **Never trust self-reports as the completion signal.** "I believe the migration is
  complete" is not evidence. Deterministic output in the transcript (test run, exit
  code, diff) is.

## No-progress rule

Three consecutive turns with the same error or no observable change → `/goal clear`
and escalate to the user with what was tried. Continuing past this point only burns
tokens on an approach that has already failed; a human decision is needed.

## Decision table — which mechanism to use

| You need | Use |
| --- | --- |
| Wait for agent-team teammates | Nothing — notifications are pushed to the lead |
| Substantial work in this session with a verifiable end state | `/goal` with the full DoD template |
| Re-check external state on an interval (CI, deploys) | `/loop`, interval matched to how fast the state changes, with declared exits |
| A completion check applied to every session, deterministically | Stop hook running a script |

`/goal` + auto mode runs unattended; without auto mode it still prompts per tool call.

## /loop exit discipline

A `/loop` must declare both exits before it starts:
1. **Success exit** — the observable condition that ends it (all tasks completed, CI
   green, queue empty).
2. **Stall exit** — N consecutive iterations with no state change → stop and escalate.

An interval loop with neither exit is the two-day incident with a timer attached.
