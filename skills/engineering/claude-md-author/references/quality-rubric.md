# Quality Rubric

Score each context file out of 100. Read the file fully, cross-reference it against the actual repo
(do referenced paths exist? do documented commands work?), then score.

| Grade | Score | Meaning |
|-------|-------|---------|
| A | 90–100 | Tight, current, universally applicable |
| B | 70–89 | Solid, minor bloat or gaps |
| C | 50–69 | Useful but bloated or missing key context |
| D | 30–49 | Sparse, stale, or mostly violations |
| F | 0–29  | Missing, severely outdated, or actively misleading |

## Criteria

### 1. Brevity & instruction budget (25 pts)
The make-or-break criterion. Long files dilute everything.

- **25** — under ~60 lines (root) or genuinely minimal for scope; every line earns its place.
- **18** — under ~100 lines; little filler.
- **10** — 100–200 lines; noticeable padding or content that belongs elsewhere.
- **0** — over 200 lines, or dense with linter's-job / task-specific content.

### 2. Universal applicability (20 pts)
Does every instruction apply to *all* tasks in this file's scope?

- **20** — no task-specific or feature-specific bleed-in.
- **10** — a few instructions that should live in a sub-scope or reference.
- **0** — substantially task-specific; reads like notes from one feature.

### 3. WHAT/WHY/HOW coverage (20 pts)
Can a fresh session understand the stack, the purpose, and how to build/test/run?

- **20** — clear project map, the *why* behind non-obvious decisions, and exact real commands.
- **12** — covers most; some gaps (e.g. missing the "why", or vague commands).
- **0** — no usable map or commands.

### 4. Non-obvious value (15 pts)
Does it capture genuine gotchas/constraints — not generic advice?

- **15** — documents the quirks a model would otherwise get wrong.
- **8** — some value, some obvious filler.
- **0** — only generic best-practice / restates the code.

### 5. Currency & actionability (20 pts)
Is it true *now*, and are instructions executable?

- **20** — commands run, paths/versions accurate, instructions concrete and copy-pasteable.
- **12** — mostly current; minor stale references.
- **0** — commands fail, paths/versions wrong, or vague/theoretical.

## Red flags (auto-deductions)

- Inlined code blocks that could be a `file:line` pointer → violates "point, don't paste".
- Exhaustive style/import/naming rules → linter's job.
- Duplicated content across files in the same tree.
- References to deleted files, wrong tech versions, or commands that would fail.
- Looks auto-generated / copy-pasted from a template without customization.
- Reactive one-off "hotfix" rules.
