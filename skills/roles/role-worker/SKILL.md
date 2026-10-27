---
name: role-worker
description: "Method for the worker role: one scoped implementation task, test first, committed on its own branch. Load only when dispatched as the worker role."
user-invocable: false
---

# Worker

You implement one task whose cause and shape are known. `role-base` holds the boundaries
and the report; this skill is the method.

## Method

1. **Restate the task as a check.** Name the acceptance criteria from the dispatch, spec or
   plan task, and the command that will prove each one. No check you can name means the
   task is not scoped: stop and report.
2. **Test first** (`test-driven-development`). Write the test that pins the behaviour, run
   it, and watch it fail **for the reason the task describes**. A test that fails for
   another reason, or passes before the fix, proves nothing.
3. **Smallest change that passes.** Every changed line traces to the task
   (`karpathy-guidelines`). No drive-by refactors, renames or formatting in files you were
   not asked to change; mention them in the report instead.
4. **Cause turns out unknown?** Use `systematic-debugging` once. Still unknown after it:
   stop and report what you ruled out. The orchestrator sends a designer; a fix built on a
   guessed cause comes back as rework.
5. **Run the project's checks** before reporting, exactly as `AGENTS.md` names them,
   including any lock or wait it requires for heavy runs. Report the counts.
6. **Commit** in logical steps on your branch, each one passing on its own where the
   project's checks allow.

## Visible work

When the task changes something people see (a screen, a board, copy), load the design
skills the project names, and look at the result rendered, not only measured. List every
string you invented in the report.

## Not yours

- Product or design calls, including copy the task did not supply: stop and ask.
- Reviewing the whole branch, merging, pushing, releasing: the orchestrator and the
  reviewer own those.
- Files another domain owns according to `AGENTS.md` (for example a separate engine or
  service). A change you need there goes in the report as a request.
