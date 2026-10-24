---
name: karpathy-guidelines
description: "How to change code without the usual LLM mistakes: surface assumptions, write the minimum code, keep the diff surgical, comment only the why, and name a check that proves it works. Use before every code change, including a one-line fix, a new function, a small script, a CI or lefthook YAML file, a migration, or an edit made through a shell command (heredoc, sed -i, perl -pi), and before reviewing or refactoring a diff. Skip it only for questions, explanations and prose docs."
license: MIT
---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Based on [Andrej Karpathy's notes](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls, read at the source, and forked from [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
by forrestchang (MIT). The comment budget, the docs and config scope of Surgical Changes, and
the trigger description are additions made in this repo.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

**Comments carry the same budget.** A comment is the one line nothing checks, so a stale
one outlives the code it described and quietly misleads the next reader. That risk is
the bar a comment has to clear.

- No comment that restates the code. `// increment i` costs a read and adds nothing.
- No docstring on a function whose name and signature already say it.
- No section banners, no `Step 1:` narration, no changelog of what you changed.
- Do write the why: the reason for this approach over the obvious one, the constraint
  that forced it, a workaround with the bug it works around, a link to the issue.

The test: delete the comment. If nothing is lost, it should not have been written.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code, documents, config, or skills:
- Don't "improve" adjacent code, prose, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code or a stale paragraph, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Fix the references your change left dangling: links, table rows, manifest entries, cross-references.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"
- "Update the doc/skill/manifest" → "Name what must now be true, then check the file says it: validate the JSON, grep every place that names the thing, run the example"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
