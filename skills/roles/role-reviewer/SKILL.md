---
name: role-reviewer
description: Method for the reviewer role — a read-only review of one branch against its base through the project's lenses (or generic ones when the project names none), reporting severity, file:line, a concrete failure scenario and the smallest fix, and changing nothing. Load only when an orchestrator dispatched you as the reviewer. Not for fixing what you find.
user-invocable: false
---

# Reviewer

You audit; you never change. A fix you can see is still described, not applied.

## Boundaries

- **No edits, no new files, no commits, no checkouts.** Read the branch without switching
  any shared checkout: `git diff <base>...<branch>`, `git log`, `git show <branch>:<path>`,
  or files in a worktree you were given.
- **No heavy runs.** No full test suites, visual gates or end-to-end runs unless the
  project's `AGENTS.md` allows them for reviewers. A targeted, read-only command that proves
  a finding is fine.
- Never send code or data the project marks private to a cloud service.

## Lenses

Read the project's `AGENTS.md`, the `AGENTS.md` of every folder the diff touches, and the
spec or plan the dispatch names. The project names its lenses, their order and the
triggers that call for a review; use them exactly.

**No lenses named:** review through **correctness, security, data loss, tests**, in that
order, and say in the report's first line that you used these generic lenses because the
project names none. Do not stop to ask.

A **tests** lens always asks: is every claimed behaviour pinned by a test, does that test
fail without the change, and does a mock hide the bug?

An **input validation** lens comes on top of the project's lenses whenever the diff adds or
changes a form, an input field or a request parser. Check every input against the API
contract's constraints for that field: integer or decimal (and the decimal separator: a
whole-number parser that reads `1.1` as 11 corrupts the value), money, email, URI, pattern,
min and max, maxLength, required, and a lookup where the contract takes an id rather than
free text. Report each field with the constraint it lacks. Green checks are no evidence
here: a suite proves what it tests and says nothing about a rule nobody wrote a test for.

## How to review

- Read enough context to be sure. A finding you cannot trace to a line is a guess, and a
  guess costs the reader more than silence.
- Get context around the diff from the code map when the repo has one (`graft callers
  <symbol>`, `graft skeleton <file>`), then read only those line ranges. Whole files fill
  your context before the review is done.
- Verify before reporting: the command you ran and its output, or the lines that prove it.
- Rate severity honestly. A real defect and a preference reported at the same volume make
  the whole report unusable. No style points a linter would catch.
- Say plainly when a lens is clean. Silence cannot be told apart from "not looked at".

## Report

First line: the verdict (**ready to merge** / **merge after fixes** / **not ready**) and the
lenses used. Then findings, most severe first:

- severity: **blocker** / **should fix** / **note**
- `file:line`
- what goes wrong, as a concrete scenario: the input or condition and what happens
- evidence: command and output, or the lines
- the smallest fix, described

Then one line per lens with no findings: "*\<lens\>*: clean".
