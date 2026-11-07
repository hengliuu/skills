# Model and effort map

The single source for which model and effort each role runs on, per harness. The Claude
Code agent files in this plugin (`agents/*.md`) must match the Claude Code
table; `tests/test_model_map.py` fails on any drift. Change a value here and in the agent
file together, in one commit.

The `sonnet`, `haiku` and `opus` aliases, and `effort`, resolve per provider. On Bedrock,
Vertex and Foundry they can map to older models that may not support `effort`.

These are defaults. The dispatch may override effort per call, and a project may raise a
role in its own `AGENTS.md` (for example worker effort `high`).

## Choosing effort per dispatch

The table sets the default. Pick the level for the task, not for the role:

- **Raise to `high`** for visual work (layout, UI states, motion and transitions, pixel checks
  on a phone width), a rebase with real conflicts, and code whose bugs lose data or money
  (payments, billing, ledgers, migrations, engines, contracts).
- **Lower to `medium`** for a designer task with no visual output, such as a root-cause
  hunt or an investigation.
- **Hand it to `chore`** when the change is already decided and only has to be applied:
  copy or punctuation passes, renames, fixture updates, guide edits, review nits with a
  named fix, cleanup. If it needs a choice, it is not a chore.
- **New motion or animation:** the designer writes the motion spec first (what moves,
  duration, easing, reduced-motion behaviour), then a worker builds it. One agent that
  designs and codes at once costs more and looks worse.
- **Keep the reviewer at `high`** for privacy, security and data-loss reviews. A missed bug
  there costs more than any saving.

Why `medium` for worker and product: the effort scale is calibrated per model, and
Anthropic's guidance starts agentic coding and multistep tool use at `medium`. Opus 5.5
defaults to `medium`. Raise a role only after a measured miss at the level below.

## The main session (orchestrator)

The orchestrator runs on the session's model, so the person sets it with `/model` and
`/effort`:

- **Default:** Opus 5.5 at `medium` for daily discussion, advice, requirements and
  planning.
- **`high`** for one session on a large decision (architecture, pricing, a hard spec).
- **Sonnet 5.5 at `medium`** for status checks and quick questions.
- **One session per topic.** Every turn re-reads the whole conversation, so a long session
  costs more per message whatever the model. Start a new session when the topic changes,
  and keep state in files (a handoff, a checklist) rather than in the chat.

## Main-session profiles

Two ways to set up the main session. Pick one when the session starts. The roles below do not
change with the profile, only who runs the main session and who checks its plan.

| Profile | Main session | Advisor | Pick it when |
| --- | --- | --- | --- |
| **Senior** | Opus 5.5 `medium` | none | The plan is not settled: an architecture, a spec, a batch whose tasks depend on each other. A wrong split sends every worker down the wrong path |
| **Goat** | Sonnet 5.5 `medium` | Opus 5.5 | The plan is approved and its task table is complete, so the session mostly dispatches, merges and fixes. The main session costs half as much per token (see the price table below), and each advisor call adds an Opus-priced read of the whole transcript on top |

Start Goat with `claude --model sonnet --advisor opus`, or run `/advisor opus` inside a session.

| Stage | Senior | Goat |
| --- | --- | --- |
| Plan | `designer` (opus) for an architecture or a spec, otherwise the main session drafts it | The main session (sonnet) drafts it, and the advisor reads it before it locks |
| Search | A read-only search agent dispatched on `haiku` | Same |
| Edit | `worker` (sonnet) | Same |
| Write tests | `worker` (sonnet) | Same |
| Run tests | `chore` (haiku), and the exit code is the verdict, never the agent's opinion of the output | Same |
| A test keeps failing | The main session (opus) reads the failure and decides | The advisor reads it, or `designer` if the cause is unknown |
| Review | `reviewer` (opus) | Same |

A visual task raises the worker to `high` and loads the project's own design skills, as in
"Choosing effort per dispatch" above.

What the advisor is and is not, from Anthropic's docs (checked 2026-11-07):

- **A nudge, not a gate.** Claude decides when to call it. It tends to consult before it commits to
  an approach, when an error keeps recurring and before it calls a task done, but no setting caps or
  forces a call. A line in the prompt such as "consult the advisor before you continue" only asks.
  The `reviewer` is the check that always runs, so Goat never depends on the advisor firing.
- **Each call re-reads the whole transcript** at the advisor's rates, and that read is not cached.
  It pays on long work and adds little to a short task. For a short task, switch the main model
  instead.
- **Claude Code and the Anthropic API only.** It is experimental, and it is not available on
  Bedrock, Vertex or Foundry. On another harness, Goat's plan check is the `designer` role or the
  human reading the plan.
- **The advisor must rank at or above the main model.** Sonnet 5.5 accepts Fable, Opus 5 or later
  and Sonnet 5.5. Claude Code does not attach a weaker advisor and shows that in `/advisor`, so
  check it there when the advisor never seems to speak.
- `--advisor` is not listed in `claude --help`. `/advisor opus` saves the choice as `advisorModel`.

**Not measured yet.** Nobody has run both profiles on the same batch. Before trusting the saving,
run one batch each way and compare how often the reviewer sends a branch back and how many tasks
are redone.

## Model cost, and why `fable` is not a saving

First-party API prices per million tokens (input / output), from Anthropic's model table
cached 2026-10-06: Fable 5.1 $10 / $50, Opus 5.5 $4 / $20, Sonnet 5.5 $2 / $10, Haiku 5.5
$0.10 / $0.50 (prompts up to 100K tokens).

Fable 5.1 is the most capable and the most expensive model, 2.5 times Opus 5.5. Its
"separate weekly limit" on a Max plan does not keep it off the main weekly limit: on
2026-10-13 a night of Fable subagents moved one account's main weekly usage from 78% to
95%. This is an observation from one account's Usage screen, not a documented rule.
Never move work to Fable to save usage.

Haiku 5.5 is a good subagent for reading, summarising and decided changes, and not a
replacement for long agentic coding or hard debugging. That is why it maps to `chore`
only.

## Claude Code

`—` means the field is absent from the agent file: the session's value applies, or every
tool is available.

| Role | `model` | `effort` | `autoCompactWindow` | `tools` | `skills` |
| --- | --- | --- | --- | --- | --- |
| orchestrator | — | — | — | — | — |
| worker | `sonnet` | `medium` | `300000` | — | `hengliuu-skills:role-base`, `hengliuu-skills:role-worker`, `hengliuu-skills:karpathy-guidelines` |
| chore | `haiku` | `medium` | `100000` | — | `hengliuu-skills:role-base`, `hengliuu-skills:role-chore`, `hengliuu-skills:karpathy-guidelines` |
| designer | `opus` | `high` | `300000` | — | `hengliuu-skills:role-base`, `hengliuu-skills:role-designer`, `hengliuu-skills:karpathy-guidelines` |
| reviewer | `opus` | `high` | `300000` | `Read`, `Grep`, `Glob`, `Bash`, `Skill` | `hengliuu-skills:role-reviewer`, `hengliuu-skills:karpathy-guidelines` |
| product | `opus` | `medium` | — | — | `hengliuu-skills:role-product` |
| project-manager | `opus` | `medium` | — | — | `hengliuu-skills:role-project-manager` |

- **orchestrator** is a skill, not an agent: it runs in the main session on the session's
  model (opus) and effort.
- **`autoCompactWindow`** is an integer number of tokens, 100000–1000000. A value such as
  `"100k"` is rejected when the agent loads, and the agent silently keeps the session's
  window. `100000` keeps every chore request inside Haiku's base price band (prompts above
  100K tokens bill at five times the rate). Local measurement: the effective window came
  out near 80,000 tokens, not a documented figure.
- **`skills`** are always namespaced. A bare `role-worker` resolves to a project or user
  skill of the same name before the plugin's own copy. Every role that writes or judges
  code also preloads `hengliuu-skills:karpathy-guidelines` (it ships in this plugin):
  an invoke the agent has to remember was skipped by one code-writing agent in seven.
- **reviewer `tools`** carries `Skill` so the reviewer can load `role-reviewer`
  itself when no skills are preloaded.
- **`fable`** is not mapped. It joins this table once it has been measured on our work (see
  the cost section above).

Precedence, highest first: the dispatch's per-call `model` / `effort`, then the agent
file, then `CLAUDE_CODE_SUBAGENT_MODEL`, then the session. `CLAUDE_CODE_EFFORT_LEVEL`
overrides every effort setting, so leave it unset in sessions that dispatch roles.

## Sources

Checked 2026-10-11 against Claude Code 2.1.296. The advisor facts in the profiles section
were read from code.claude.com/docs/en/advisor on 2026-11-07 and not run locally. The `autoCompactWindow`
range and the namespacing rule came from a local `--plugin-dir` experiment.
