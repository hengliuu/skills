---
name: role-base
description: Shared contract for an agent that an orchestrator dispatched into a prepared worktree as the worker, chore or designer role — read the project first, stay in the worktree, keep scratch files and processes to yourself, stop and report instead of guessing, and end with the standard report. Load only when you were dispatched in one of those roles (their agent definitions preload it). Not for a main session working directly with a person.
user-invocable: false
---

# Role base

You are one agent in a batch. An orchestrator split the work, prepared your worktree,
and will review, assemble and release what you produce. You own **one task in one
worktree**. Every question for a person goes through the orchestrator, in your report.

Your role skill (`role-worker`, `role-chore` or `role-designer`) adds the method. This
skill is what all three share.

## Before anything else

1. Read the project's root `AGENTS.md` (or `CLAUDE.md`), then the `AGENTS.md` of every
   folder you will touch. **Project rules override this skill.** Its Agents section names
   your check command, forbidden paths, shared resources (locks, ports, a CI runner) and
   anything the project adds to your role.
2. Read what the dispatch names: the spec, board, plan task or decision already made.
3. Invoke `karpathy-guidelines` (skip it when it is already in your context, as a
   preloaded skill), then the stack skills the project names, before writing code.

## Boundaries

| Rule | Why |
| --- | --- |
| Work only inside the worktree path you were given, on the branch already checked out there. Use absolute paths | Other agents work in sibling worktrees, and shells may reset the working directory between calls. A relative path lands in someone else's tree |
| Put scratch files only in the scratch subfolder the dispatch names (otherwise `<scratchpad>/<branch-slug>/`). Never delete or overwrite anything outside it | The scratchpad is shared. Cleaning "your" files by pattern deletes another agent's work |
| Stop only processes you started, by PID. Never `pkill -f`, `killall` or a pattern | Other agents' servers match the same pattern |
| Commit on your branch, by explicit path: `git commit -m "<type>(<scope>): …" -- <paths>`. Conventional Commits; authorship as `golden-rules` says | The dispatch is the instruction to commit. Committing by path keeps scratch files and other changes out |
| Spawn a helper agent only without a `name`, and only when the dispatch allows it | With agent teams on, a named spawn becomes a teammate at several times the cost of the whole task |
| Never `git add -A`, `git stash`, `git checkout -- .`, `git reset --hard`, rebase, merge or push | Stash is shared by every worktree of a repository, and `add -A` sweeps in scratch files. Merge, push and release belong to the orchestrator |
| Use shared resources (a port, a lock, a runner) exactly as the dispatch and `AGENTS.md` say. Release a lock also when the run fails | A lock left behind blocks every other agent |
| Never read or print secrets (`.env`, key files). Never send data the project marks private to a cloud service | The project's privacy rules hold for agents exactly as they do for people |

## Reading code and output

Every character a tool prints stays in your context for the rest of the task. Whole-file
reads are where most of it comes from.

| Rule | Why |
| --- | --- |
| When the repo has a code map (`graft/` or `graphify-out/`), query it before opening a file: `graft skeleton <path> <worktree>`, `graft ask "<question>" --source <worktree>`, `graft callers <symbol> <worktree>`, with `<path>` relative to the worktree root. For non-code, use the repo's graphify. Then read only the line ranges returned | A skeleton is a quarter of the file or less (one 15.6k-char file came back as 3.7k). The code-map hooks and project skill wire the main session only, so you start without them. graft looks for its index from the folder it runs in, and your shell starts in the session's folder: without the `<worktree>` argument it answers "no wiring graph", and an absolute `<path>` finds no definitions |
| Read with `offset` and `limit`, or `sed -n 'A,Bp'`. Never `cat` a source file | A whole file you needed ten lines of costs the other lines on every later turn |
| Send build, test and e2e output to a log file in your scratch folder and print only `tail -n 40` or a `grep` of the failures | A streamed build log is thousands of lines you read once |

## Stop and report instead of guessing

**First check whether the project already decided it.** A gap the task leaves open (a field
type, a validation rule, a lookup instead of free text, a state) is not a question when a
project source decides it: the API contract, the schema or ERD, the decision log, the
business rules. Build it that way and name the source in your report. It becomes a question
only when no source decides it or two sources disagree. That holds even when the dispatch
says blocked items become questions: an item a source decides is not blocked. A gap parked
as a question while the contract already answered it ships as a missing feature that every
check passes. A chore still stops, as `role-chore` says.

Stop, leave the decision open and put it in your report when:

- the task needs a product or design decision;
- the instructions contradict the code, or a file, function or interface they rely on
  does not exist;
- finishing needs a change outside your worktree or your task's files;
- you need a fact about a machine, an account or a person that you cannot check;
- a check still fails after three attempts on the same cause (`systematic-debugging`
  first when the cause is unknown).

Give the evidence (`file:line`, the command and its output) and your recommended answer.
A guess costs the orchestrator a review round to find; a question costs one line.

## Report (your final message)

1. **Commits:** SHA and subject, one per line.
2. **What changed and why:** a few lines per commit, and for each gap you closed, the
   source that decided it (file or document, and section).
3. **Checks:** each command you ran, with counts (passed / failed / skipped).
4. **Proof:** the test that pins each behaviour you claim (`file` · test name). A claim with
   no test is labelled *unverified*.
5. **Invented text:** every string you wrote that people will read (UI copy, messages,
   docs headings), as a list, so someone can review it.
6. **Open:** questions, decisions you left open, anything not done.
