# Contributing

Thanks for helping. A few rules keep the repo coherent.

## Before you open a pull request

- Run the checks CI runs: `python3 scripts/validate_skills.py`, the hook tests
  (`python3 -m unittest discover -s hooks/tests`, and the same for
  `skills/roles/role-orchestrator/tests`), and `claude plugin validate . --strict`.
- Hooks must run on Python 3.9, macOS's `/usr/bin/python3`. Run their tests with it too.
- Bump the `version` in `.claude-plugin/plugin.json` on every change in behaviour. Claude
  Code only delivers an update when the version changes.

## Writing skills

- One skill, one job. The `description` says what it does and when to use it, under
  1,024 characters. Keep `SKILL.md` under 500 lines and move detail into `references/`.
- Explain why a rule exists instead of shouting it. A model that understands the reason
  handles the cases the rule did not foresee.
- Use placeholders instead of a real project's names and paths.
- New prose has no semicolons and no em dashes. Short sentences read better to people and
  to models.

## Third-party skills

Never copy a third-party skill into this repo. Copying strips its own hooks and agents and
freezes it at the copied version. Link to it in the README instead, and if a plugin needs
it, check for it in a SessionStart hook.

If an upstream skill already does the job, drop ours rather than shadowing it. Two skills
with one name make resolution a coin flip.

## Layout

```
.claude-plugin/marketplace.json   marketplace manifest (this repo is the marketplace)
.claude-plugin/plugin.json        plugin manifest, with an explicit list of every skill
skills/<category>/<skill>/        SKILL.md plus references/ when needed
skills/<category>/README.md       one line per skill
agents/                           Claude Code agent wrappers for the roles
hooks/                            hooks.json, scripts and tests/
templates/                        starter AGENTS.md for new repos
docs/                             install guide for every harness
scripts/validate_skills.py        the skill and manifest checks CI runs
```
