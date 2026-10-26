# The task table every plan carries

A plan ends in one table. It is what makes the [execution tier](../SKILL.md#picking-an-execution-tier)
a lookup instead of a guess, and it is what an orchestrator dispatches from. `writing-plans`
(superpowers) does not write it on its own, so ask for it when the plan is written, and add
it to an approved plan that lacks one before picking a tier. `egm-draft` does not write it
either: on the EGM path, add it after the approved design doc's build steps, and that doc is
the plan.

## Format

| # | Task | Depends on | Files it writes | Role | Effort | Check |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Settings parser keeps unknown values | none | `<module>/settings/**` | worker | medium | the settings unit tests |
| 2 | Adapter for a second payment provider | none | `<module>/payments/**`, `tests/payments/**` | worker | high | the adapter's tests |
| 3 | Settings screen offers the new provider | 1, 2 | `web/src/features/settings/**` | worker | high | frontend tests and the visual gate |
| 4 | Docs page for the new option | 3 | `docs/**` | chore | medium | the docs lint |
| 5 | Review before merge | 1, 2, 3, 4 | none (read only) | reviewer | high | findings list |

- **Task:** one outcome a person can verify, small enough for one worktree and branch.
- **Depends on:** the numbers of tasks that must land first, or `none`. A task needs another
  one when it reads that task's output or builds on its code.
- **Files it writes:** paths or globs. This is what decides whether two tasks can run at once.
  Read-only tasks write `none`.
- **Role:** `worker`, `chore`, `designer`, `reviewer`, `product`, `project-manager`, or a project agent that the
  project's `AGENTS.md` names. Use `chore` only when the change is already decided and only
  has to be applied. Without the roles installed, write the role anyway: it still tells a
  solo run which tasks need judgment.
- **Effort:** the role's default from the role-orchestrator model map
  (`role-orchestrator/references/model-map.md`, when that plugin is installed), raised for
  visual, motion or layout work, conflicted rebases, hard debugging and code whose bugs lose
  data.
- **Check:** the command or artefact that proves the task is done. A task without one is not
  ready to dispatch.

## Reading the tier off the table

Go down this list and stop at the first line that fits.

1. Every task depends on the one before it, or the tasks write the same files: **solo**
   (`executing-plans`).
2. Tasks are independent, write different files, and land as one branch you assemble
   yourself: **`subagent-driven-development`**.
3. Tasks are independent, write different files, and each should get its own worktree,
   branch and review before a batch merge: **`role-orchestrator`** (from the roles skills).

Two tasks that write the same files never run at the same time, whatever the tier. Order
them with a dependency instead. A pick that is still unsure after reading the table is shown
to the human with both candidates.
