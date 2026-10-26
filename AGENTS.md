# skills

A personal agentic engineering workflow, distributed two ways from one tree: as a single Claude Code
plugin (`hengliuu-skills`, and this repo IS the plugin and its marketplace), and as a skills package any
harness can install with `npx skills add <repo>.git`. There is no application code, everything is
skills, context, hooks and manifests. Read `README.md` for what's inside and how to install it.

## Repo map

- `.claude-plugin/marketplace.json` — marketplace manifest (`hengliuu`), one plugin with `source: "./"`.
- `.claude-plugin/plugin.json` — the plugin manifest. Its `skills` array lists every skill directory
  explicitly, because skills sit in category folders. `scripts/validate_skills.py` fails on an orphan
  or a missing entry.
- `README.md` — overview and install only. Workflow detail belongs in `WORKFLOW.md`.
- `skills/<category>/<skill>/SKILL.md` — each category folder has a `README.md` with a one-line table.
  - `skills/workflow/` holds `golden-rules` (its `AGENTS.md` is the working-style rules, injected every
    session by the SessionStart hook), `workflow-map` (the router: it owns the stage-to-skill table and
    the execution-tier decision, so those live in exactly one place), `intent-capture`, `commit-group`
    and `loop-discipline`.
  - `skills/engineering/` holds `karpathy-guidelines` and `claude-md-author`.
  - `skills/roles/` holds `role-orchestrator` (a main session running a batch of independent tasks, one
    worktree each, merged by cherry-pick) and seven `role-*` skills that carry each role's method, so
    they travel to any harness. `role-orchestrator/references/model-map.md` is the single source for
    model and effort per role and harness. Change a value there and in the agent file together, then
    run `python3 -m unittest discover -s skills/roles/role-orchestrator/tests`. Role skills never set
    `disable-model-invocation` (it blocks preloading). They use `user-invocable: false` and a "load
    only when dispatched" description. No project names in them: a project's ports, locks and checks
    belong in that project's `AGENTS.md` Agents section.
- `agents/*.md` — thin Claude Code wrappers for the six roles: frontmatter (model, effort,
  `autoCompactWindow`, preloaded skills) plus a two-line body, nothing else. They preload skills by
  **namespaced** name (`hengliuu-skills:role-worker`) because a bare name resolves to a project or user
  skill of the same name first. `autoCompactWindow` takes an integer (`300000`, never `300K`: that is
  rejected at load with only a debug-log warning, and the agent keeps the session's window).
- `hooks/hooks.json` — all hooks of the plugin. The SessionStart hook injects the Golden Rules and warns
  when the superpowers prerequisite isn't installed (it accepts a plugin install or a skills-CLI install
  in `~/.claude/skills/` or project `.claude/skills/`).
  - `hooks/gate.py` (PreToolUse) is the one-shot karpathy and review gate for the main session, plus an
    always-on deny of a subagent's named Agent spawn, off with `HENGLIUU_GATES=off`.
  - `hooks/map_gate.py` is its subagent-only sibling: per file, a large source file is read through
    graft before its lines reach the agent's context.
  - `hooks/dispatch_check.py` adds a model-map and a tier note to role dispatches and never blocks. It
    finds agent files at `${CLAUDE_PLUGIN_ROOT}/agents/<role>.md`, falling back to the repo root.
  - `hooks/check-codebase-map.sh` carries two session-start checks, both silent unless they fire:
    graft's telemetry (opt-**out**, so a plain install sends until someone disables it, and the hook
    reads `~/.graft/telemetry.json` directly rather than spawning graft) and the codebase-map nudge,
    which needs a build manifest and neither `graft/` nor `graphify-out/`. It stays **tool-agnostic on
    purpose**: both map tools are 0.x shipping weekly, so the always-injected rule names the behaviour
    and the hook reports what is on disk. Both ship their own wiring, so never add a competing set here.
  - Hooks must run on Python 3.9 (macOS's `/usr/bin/python3`): no backslash inside an f-string
    expression, and `from __future__ import annotations` wherever `X | None` appears. Run
    `python3 -m unittest discover -s hooks/tests` after changing them, and again with `/usr/bin/python3`.
- `WORKFLOW.md` — the six-stage lifecycle: which skill runs each stage, the human gates, the execution
  tiers, and the stages still missing. README links here rather than describing the workflow itself.
- `templates/` — what people copy out by hand. `project-level/AGENTS.md` is the starter for project
  repos (not for this repo), with `AGENTS.md.example` beside it filled in for a made-up project.
  `context/AGENTS.md` and `agents/reviewer.md` are **symlinks** into `skills/` and `agents/`, so there
  is one copy of each and no drift.
- `docs/install.md`, `scripts/validate_skills.py`, `.github/workflows/ci.yml` — install guide, the skill
  and manifest checks, and CI.

## Rules for editing this repo

1. **Placeholders, never project names.** Skills must stay project-agnostic:
   `<org>/shared` = shared utilities package.
   Never let a specific project's import paths or product names leak in.
2. **Version bump on every behavioral change.** Bump
   `plugin.json` version. The working-style rules carry **no version of their own** —
   the skills CLI tracks them by content hash and names them in `npx skills update`,
   which is a signal that cannot drift the way a hand-typed number does. Bump
   `marketplace.json` metadata version with it. Do both **in the same
   commit** as the change — a skill edit without a version bump is an incomplete change
   (installed caches key on the version and will not pick it up).
3. **Never vendor a skill we don't own** (superpowers, graft, graphify, grill-me, …) — list it in README's "Builds on"
   section and have the depending plugin check for it in a SessionStart hook.
   **One recorded exception, below, and no others.** Vendoring strips the skill's own hooks and agents and freezes it
   at the copied version. The rule extends to skills we wrote: when an upstream ships
   one that does the job, delete ours. Not because of a name clash — plugin skills are
   namespaced, so `hengliuu-skills:grill-me` and a bare `grill-me` stay separately
   addressable and neither overrides the other. The cost is two near-identical
   descriptions competing for the same trigger, and a worse copy to keep in step with
   upstream. That is why `grill-me` went: mattpocock's is agent-backed and deliberately
   `disable-model-invocation`, and ours was ten lines.
   **The exception is `karpathy-guidelines`**, a deliberate fork of
   [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
   (forrestchang, MIT per its manifest, compared at upstream `2c60614`). It stays ours for
   three reasons: it carries team rules upstream lacks (the comment budget, surgical changes
   to docs, config and skills), its description triggers where upstream's does not (5 of 6
   live sessions against 2 of 6, 2026-10-17), and role agents preload it by a stable
   `hengliuu-skills:` name. Before editing it, diff upstream and take what it added since.
4. **`golden-rules/AGENTS.md` is the single source of truth** for team working
   style, and it is **injected into every session** — so it is an instruction budget, not a knowledge
   base. The budget is attention, not line count: frontier models follow roughly
   150–200 instructions before adherence degrades (smaller models decay faster), and
   Claude Code's own system prompt already spends part of that. Judge a line by what it
   changes, not by how much room is left. Rules for what belongs:
   - Every rule must earn its place in a session that does **not** trigger it. A rule
     that only applies to one workflow belongs in that workflow's skill.
   - State the trigger and the **why**, then point at the skill for the mechanics.
     Never copy a skill's steps into this file — that's the failure mode it exists to
     avoid.
   - Section headings should say when they apply (e.g. "only when a plan file exists"),
     so a session that doesn't match can skip the whole block.
   - Don't duplicate its content into README or skills — link to it.
   - One rule = one imperative plus the consequence of ignoring it. Prose gets averaged;
     an imperative with a stated cost gets followed. Decisions belong in a table, so
     they read as a lookup rather than a narrative.
   - Cut persuasion. An argument for why a tool is worth installing changes nothing in
     a session where the tool is absent, and costs attention in every session where it
     is present. That argument belongs in README.
5. **Keep JSON valid** — after editing any manifest: `python3 -m json.tool <file>`.
6. **Plugin skills follow the standard SKILL.md format**: frontmatter `name` +
   trigger-rich `description`, body kept lean, details in `references/*.md` loaded
   on demand.
7. **Adding or removing a skill is a five-place change.** The skill folder, the `skills` array in
   `plugin.json`, the category `README.md` table, the plugin descriptions in `plugin.json` and
   `marketplace.json` when they name skills, and the root README ("What's inside" table and Layout
   block). Manifests silently drift from reality otherwise, and they are what users read before
   installing. `scripts/validate_skills.py` catches a skill that is missing from `plugin.json` or listed
   without a folder. **Check `.gitignore` first**: a skill folder that is gitignored is local-only and
   must stay out of all published descriptions, however real it looks in the working tree.
8. **Verify claims against the docs before writing a hard rule.** Skills here assert
   things about the harness (agent teams need `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`;
   a team runs ~7× the tokens of a solo session).
   Each was checked against upstream docs or a live API, and each carries its
   consequence in-line. Don't add a rule from memory — a confidently wrong rule in an
   always-loaded file is worse than no rule.

9. **Only skills cross the harness boundary.** `npx skills add` installs skill folders
   and nothing else — hooks, `agents/`, and manifests stay behind, so anything a
   non-Claude-Code user must have belongs **inside a skill folder** or in `templates/`
   with a README step telling them to copy it. That is why the working-style rules live
   in `golden-rules/` rather than a `context/` directory: it is the only way they
   travel. Before adding a non-skill asset, decide which half of the team it serves.

10. **Refer to a skill by its bare name; never write a slash command.** The working-style
   rules and the skill bodies are copied into other harnesses (Kiro steering files, Cursor
   global rules, `.agents/skills/`), where `/hengliuu-skills:commit-group` is not merely
   irrelevant — it names nothing, because there is no plugin namespace there. A bare
   `commit-group` is correct everywhere: the model maps it to whatever the local harness
   calls it, which is the harness's job and not the document's. Slash commands with the
   `plugin:skill` prefix belong in README only, which is Claude-Code-specific by design.

## Submitting changes

Work on a branch, never on `main`, and open a pull request on GitHub.

1. Branch from `main`: `git switch -c <type>/<short-topic>`.
2. Make the change with its version bump (rule 2) and run the checks that match what you
   touched: the unit tests named in the repo map, `python3 -m json.tool` on each manifest,
   and `claude plugin validate . --strict`.
3. Commit with Conventional Commits (`feat(roles): ...`, `fix(hooks): ...`), one logical
   change per commit.
4. Open the pull request against `main`. Say what changed and why, and list the checks you ran.
5. A maintainer reviews and merges. Squash-merge keeps `main` readable.

## Testing changes locally

Add the working copy as a local marketplace and reinstall:

```
/plugin marketplace add /path/to/skills
/plugin install hengliuu-skills@hengliuu
```

Then open a new session and confirm the working-style rules were injected and the skills
appear (namespaced, e.g. `hengliuu-skills:karpathy-guidelines`).

## Renames

The plugin and marketplace names are part of the install commands users run. If either is renamed,
update: `marketplace.json` (name), `plugin.json` (name), every `hengliuu-skills:` namespace in agent files,
the model map and `hooks/dispatch_check.py`, README commands and `docs/install.md`. Note that
`/plugin install X@Y` takes the marketplace manifest's `name`, never the repo path. Renaming the
marketplace forces every existing install to be redone, so say in the commit that existing installs must
reinstall under the new name.
