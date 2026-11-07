---
name: jev
description: Use TypeSafe Jev, a fast and cheap judgment model, to score, rank, filter or triage many items in one parallel pass (name candidates, review findings, search hits, backlog items, test failures), to re-pick each plan task's role and effort before dispatching agents, and to run diff quality gates before a code review. Use when a task needs more than a handful of repeated yes/no, pick-one or rating judgments, or when the user says "pakai Jev", "score these", "ranking", "filter" or "triage". Needs the user's own TypeSafe key. Not for building Jev into an application.
---

# jev

The LLM writes; Jev decides. Jev answers typed questions about a `state` in about a second
for a fraction of a cent (check TypeSafe's own pricing page, it changes), and returns
probabilities, never prose. Use it where a list is too long to judge carefully by hand.

**Jev is a filter, not a judge.** It reasons well about meaning (does this name fit the
story?) and poorly about facts it cannot see (is this name already taken?). Every result
is a lead: check facts with the web or the code before acting, and leave the decision to
the user when it is theirs.

**Jev is a cloud service.** Never send client data, transcripts, secrets, or anything from
a folder the project marks as confidential without the user's OK in this session.

## When Jev is the wrong tool

Jev never fails loudly: a bad fit still comes back as a clean, confident number. So the
check happens before the call, not after it.

- **Anything generative.** Writing, summarising, explaining stay with the LLM; Jev only
  picks from answers you defined.
- **A handful of items.** Five judgments are faster to make in the conversation than a
  request file is to write. Jev pays off at volume, or when the same question repeats.
- **Judgments whose value is the nuance.** "Is this argument persuasive" loses what matters
  once squeezed into three levels. Keep those in the conversation, or with the user.
- **Categories still being discovered.** If the options change with every batch, the
  schema is not ready; settle it on a few items by hand first.
- **Facts it cannot see** (is the name taken, does the test pass). Give it the evidence in
  `state`, or check the fact directly instead.

## Decision points in workflow skills

The `workflow-map` skill (Decision points) writes its routing calls as typed
decisions: a closed option → meaning table, the evidence to read, and whether the call is
reversible or consequential. Those tables are already Choice schemas. That's the one case
where a single judgment is worth sending to Jev, because the question is fixed and repeats
across every session, so the request costs nothing to write. The value isn't speed. Jev
is a second, independent reader of the same evidence, and its probabilities tell you when
to ask the user.

Only in a folder listed in `hooks_allow`, because the evidence is repo content:

1. **Pick first, then ask Jev.** Write down your own pick from the table before calling
   Jev, so its answer can't anchor yours.
2. **Build the Choice from the skill's table verbatim.** `criteria` is the option →
   meaning table, and `state` holds the evidence the skill names (the diff, the request
   text, the task's file list), never your conclusion. For a list (commit-group files,
   plan tasks, duplicate candidates) send one item per entry in a single run.
3. **Combine the two picks.**

   | Your pick vs Jev | Jev `confidence` | Treat as |
   | --- | --- | --- |
   | Same | ≥ 0.75 | **sure** |
   | Same | < 0.75 | sure, but mention it was close |
   | Different | any | **unsure**: show both candidates and the evidence |

4. **Authority doesn't change.** A consequential decision (commit, ticket, spawning a
   team, closing a plan) still waits for the user, however sure both of you are.

Outside the allowlist, or when Jev fails, make the pick alone as the skill describes. The
0.75 cut is a starting point. Tune it once a few real decisions show where Jev and the
outcome disagree.

### Role and effort before dispatching agents

The most frequent decision point. Before `role-orchestrator` or `subagent-driven-development`
dispatches a plan, run its task table through Jev. The plan's Role and Effort
columns are your pick from step 1, so the steps above happen in one command:

```bash
python3 <skill-dir>/scripts/jev.py route <plan.md> [--out result.json]
```

It sends each task's text, files and check (never the plan's own role and effort), places it
on role-orchestrator's role-and-effort rows, and prints Jev's pick, the model that role runs
on (`model-map`), and a verdict per task:

| Verdict | Do |
| --- | --- |
| sure | Dispatch as planned |
| sure, but close | Dispatch as planned, and mention it was close |
| check the effort | Same role, other effort: read the task again, and raise it if it is visual, conflicted, or code whose bugs lose data or money |
| UNSURE | Different role: show both to the human before dispatching that task |
| project agent | Not on the rows: yours to judge |

UNSURE rows still exit 0; only a failed request exits 1. Escalations (xhigh after a miss at
high, a designer after a worker failed twice) depend on history the task text does not
carry, so they stay your call.

Pilot on 2026-10-16 with the 12 tasks in `tests/fixtures/route-pilot.md`, whose answers were
known (jev-1.14.0, under 1 s): 11 matched in each of three runs, the miss being the
payment adapter (plan `worker-high`, Jev `worker-medium`, reported as "check the effort").
Naming money (payments, billing, ledgers, migrations) in the `worker-high` row made it 12 of
12 in three runs. Those words now appear in two fixture tasks, so the fixture no longer tests
that row blind: check the next real plan's money tasks by hand. Rerun it from an allowlisted copy after changing the options.

## Quality gates while engineering

Jev can't choose between designs or approaches. That judgment is all nuance, and it
comes back as a confident number that means nothing. It is good at the same narrow
question asked over many items of a finished change. Run these before
`requesting-code-review` on a diff larger than a handful of hunks, in allowlisted
folders only:

| Gate | Per item | Question (Noul) | Evidence in `state` |
| --- | --- | --- | --- |
| Algorithm | changed function | Inside a loop over the input, does it repeat a linear scan (`in` on a list, `.index`, `.remove`, a nested loop, filtering a list) where a set or dict built once would remove it? A loop over a small constant, or inherently pairwise work, doesn't count. | the function's code |
| Scope | diff hunk | Does this hunk serve the stated request? | the request text + the hunk |
| Comments | added comment | Does this comment only restate the line below it? | the comment + the next few lines |
| Findings | review finding | Is this finding a real defect, rather than a style preference? | the finding + the code it cites |
| Failures | failing test | Does this failure share a cause with the first failure? | both error outputs |

Pilot on 2026-09-28 with synthetic labelled code (jev-1.13.0, under 1 s per gate):

| Gate | Correct | Notes |
| --- | --- | --- |
| Algorithm | 9 of 10 | The miss was a nested-loop two-sum, which landed at 0.49, in the unsure middle, not a confident wrong answer. |
| Scope | 6 of 6 | |
| Comments | 6 of 6 | |

These are small pilot sets. Re-check the cuts on real diffs before trusting them.

**Algorithm, Scope and Comments run in one command** from the repo root. Pass the user's
request as they stated it, not your summary of the change:

```bash
python3 <skill-dir>/scripts/jev.py gate --request "<what was asked>" [--base main] [PATH ...]
```

Without `--base` it reads the uncommitted change plus untracked files. With `--base` it reads
everything since the merge base. Untracked files that are not gitignored are sent whole, so
check `git status` first. It skips lockfiles and minified files, runs Comments on code files
only and Algorithm on non-test code only (with the enclosing function as evidence), refuses a
repo whose root is outside `hooks_allow`, and stops at 80 items (pass paths to narrow it). Each item gets a risk from 0 to 1: **leads** (0.6 and up) and
**unsure** (0.4 to 0.6) are listed, the rest pass silently. `--out FILE` keeps every score.
Findings and Failures need inputs a diff doesn't hold, so they still go through a request file.

An Algorithm lead is a candidate for a set/dict rewrite. Confirm it against the real input
size before changing anything. A Scope lead is a candidate for scope creep. Read it and
either justify it or revert it. A Comments lead is a candidate for deletion. These are
leads to check, never automatic edits, and the unsure ones are yours to judge.

## Run it

Write a request file in the scratchpad (`<skill-dir>` is the folder this SKILL.md sits in), then:

```bash
python3 <skill-dir>/scripts/jev.py request.json [--out result.json]
```

The key comes from `TYPESAFE_API_KEY`, then the key file `~/.claude/jev/key`, then the macOS Keychain
(service `TYPESAFE_API_KEY`). A first-time user runs `python3 <skill-dir>/scripts/jev.py setup`: it
stores the key, adds allowed folders and tests the key. `jev.py allow FOLDER` and `jev.py allowed`
edit and list `hooks_allow`.
Never print it. `jev.py --check` sends one tiny synthetic request and says whether the key
works and where it came from. On a 401 the stored key is stale: ask the user to run
`python3 <skill-dir>/scripts/jev.py key` in a terminal (it prompts for the key, so it never enters
the conversation, and tests it afterwards). A `TYPESAFE_API_KEY` exported in the shell overrides a
stored key. Do not go looking for the key in other files. The router hook also reports a rejected key once per session.

```json
{
  "context": {"product": "what every item is judged against"},
  "items": [{"id": "Tilas", "state": {"name": "Tilas", "meaning": "retrace the steps"}}],
  "questions": {
    "fit": {
      "type": "score",
      "instructions": "How well does `item` express `context.product`'s story?",
      "criteria": ["No link", "Related but not the story", "The story itself"]
    },
    "taken": {"type": "noul", "instructions": "Is `item.name` a common product name?"}
  }
}
```

One request per item, 8 in parallel; all questions in a request run in parallel and cannot
see each other's answers. Use `"state"` instead of `"items"` for a single request. Output
is `{id: {question: answer}}`; a usage line goes to stderr. An item that fails gets
`{"error": ...}` instead of answers and the exit code is 1; the other items are kept, so
rerun only the failed ids. A rejected key aborts the whole run.

## Write good questions

- **Noul** — yes/no, returns `noul` 0–1. Near 0.5 means unsure, not "medium".
- **Choice** — one of named options (`criteria` maps option → meaning), returns `choice`,
  `probabilities`, `confidence`.
- **Score** — ordered levels (`criteria` is a list, 2–10 concrete levels), returns `score`
  (can land between levels), `probabilities`, `confidence`.
- Question ids are never sent to the model: put the whole meaning in `instructions` and
  `criteria`. Point at state fields with backticks (`item.name`).
- Give evidence, not conclusions: the text, the diff, the sources — not "the researcher
  finished".
- One narrow judgment per question; split independent dimensions and combine them in code
  with explicit weights. Confidence is not accuracy; thresholds need checking on real cases.
- **Choice options must not overlap, and must cover every case.** With "urgent" and "high
  priority" both on the menu, Jev still answers confidently, just inconsistently — the
  schema is broken, not the model. Add a "none of these" option when an item may fit none.
- Don't ask Jev how confident it is; every answer already carries `probabilities` and
  `confidence`, and a "confidence" question only adds a second, uncalibrated guess.
- **Pilot before a big run.** Send the questions for 3–5 items whose answers you already
  know. If Jev gets those wrong, fix the question or the evidence — not the threshold.

## Then

Sort in code, show the user the top of the list with the scores, and check the survivors
(web, code, tests) before recommending one. Say how many items and tokens the run used.

Don't let a threshold hide the unsure middle. Pick the cut per question from what a wrong
answer costs (a wrong "drop" loses a good item; a wrong "keep" only costs a later check),
and treat items near 0.5 or below the confidence cut as undecided: judge those yourself or
show them to the user as unsure, rather than silently keeping or dropping them.

## The hooks

Two hooks use the same client (`scripts/hook_router.py`, `scripts/hook_stop.py`), plus a
session-start check (`hooks/check-jev.sh`). They need Claude Code and run only in folders
listed in `hooks_allow` in `~/.claude/jev/config.json`, because they send the prompt or the
final message to TypeSafe. Until `hooks_allow` is set, no folder is on. Add a folder only after
the user confirms it holds no client data.

- **Skill router** (UserPromptSubmit): one Noul per skill in `router_skills` names the
  skills a prompt calls for. Outside the allowlist, with no key, or on any failure it adds
  nothing, and the prompt goes through unchanged.
- **Unverified-done check** (Stop): when a turn edited files other than prose (`.md`,
  `.mdx`, `.txt`, which no command can verify), Jev judges whether the final
  message claims success that no command verified. Above `stop_threshold` the stop is
  blocked once, never in a loop, with a request to verify or say what is unverified.

Setup, the key lookup, every config key and troubleshooting are in
[references/setup.md](references/setup.md). The user's `config.json` overrides the shipped
`config.default.json`, and a `router_skills` entry set to `null` drops a default skill.

After changing any script, run the offline tests (Jev is faked, nothing is sent):
`python3 -m unittest discover -s <skill-dir>/tests`, with `/usr/bin/python3` too, since hooks must run on 3.9.
