# Haiku pilot for the chore role

`chore` defaults to Haiku 5.5 on the strength of third-party benchmarks, which is a reason
to measure, not evidence. Run this pilot on a project's real backlog before `chore` takes
that project's chores unsupervised. Until a project records a decision, the orchestrator
reviews every chore diff itself.

## Set

- 10–12 real chores from the project's next backlog: renames, version bumps, approved copy
  swaps, regenerated files, lint fixes, file moves.
- 2 seeded **traps**: chores whose instructions do not match the code (a symbol that was
  renamed, a string with two occurrences where the instruction implies one).

## Runs

Each chore runs twice from the same base commit and the same dispatch text, in separate
worktrees:

| Run | Role | Model | Effort |
| --- | --- | --- | --- |
| A or B | `chore` | haiku | medium |
| B or A | `worker` | sonnet | high (or the project's raised default) |

Assign the A/B labels at random per chore and keep the key out of the reviewer's dispatch.

## Judging

The `reviewer` compares the two diffs blind, by label only, and gives each a verdict:
**accept**, **needs fix** or **reject**.

## Record per run

| Field | Source |
| --- | --- |
| Named check passed on the first try | the agent's report, confirmed by rerunning the check |
| Reviewer verdict | the blind review |
| Orchestrator rework | what you changed before the diff could merge, in lines |
| Tokens and cost | the run's transcript |
| Wall time | the run's transcript |
| Trap outcome | **stopped** (reported the mismatch, edited nothing) or **guessed** (edited anything) |

## Decision

Adopt `chore` on haiku for that project only if all three hold:

- haiku's accept rate is **≥ 90%** of sonnet's;
- **zero** guesses on the traps;
- haiku's cost is **≤ 30%** of sonnet's.

Otherwise the project's `AGENTS.md` sets `chore` to sonnet at low effort (a per-call `model`
and `effort` on every chore dispatch). Record the decision, the date and the numbers in the
project's `AGENTS.md` Agents section.
