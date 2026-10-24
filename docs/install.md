# Installing

The short version is in the [README](../README.md#install). This page covers every harness, the global context, updates and troubleshooting.

## Global context (mandatory)

**What it is.** A single file,
[`skills/workflow/golden-rules/AGENTS.md`](../skills/workflow/golden-rules/AGENTS.md),
titled *Golden Rules*. It is short on purpose. It covers code work, review,
commits, how to start a piece of work, plan files, agent teams, codebase maps and
autonomous runs. For each it states the rule and points at the skill that carries the
mechanics.

**Why it is mandatory.** A skill only runs when something makes the agent reach for it,
and this file is that something. It says "invoke `karpathy-guidelines` before writing
code", "offer `commit-group` instead of committing inline", and "start at `workflow-map`
when the next step isn't obvious". Skip it and the skills sit installed but unused, and
the agent falls back to its defaults: it commits on its own, calls work done without
running it, and skips review.

**How it reaches a session.**

| You use | How the rules load | What you do |
|---|---|---|
| Claude Code with the `hengliuu-skills` plugin | The plugin's SessionStart hook injects them | Nothing |
| Any other harness, or Claude Code without the plugin | Nothing loads them automatically | Link the file once: [per-harness steps](#load-the-global-context-per-harness) |

**Where the file comes from.** The `golden-rules` skill exists only to carry it.
It never runs on its own. Install it with the skills CLI and the file lands at:

```
~/.agents/skills/golden-rules/AGENTS.md
```

`npx skills update` refreshes that file whenever the rules change. **Link to it, don't
copy it.** A link picks up every update automatically, while a pasted copy quietly
goes stale.

**Project files win.** A project's own `AGENTS.md` / `CLAUDE.md` overrides these rules
where the two conflict.

**Check it loaded.** Open a *new* session and ask:
*"What do the Golden Rules say about commits?"*. A loaded session answers with
`commit-group` and says push is always manual. An agent that has to search for the
answer, or doesn't know it, has not loaded the file.

## Setup on Claude Code

1. **Install superpowers** (mandatory: the plugin warns at session start if it's
   missing):
   ```
   npx skills@latest add obra/superpowers -a claude-code -g
   ```
   `-a` picks the harness (`claude-code`, `opencode`, `codex`, `gemini-cli`, `antigravity`,
   `kiro-cli` and more, or `-a '*'` for all), `-g` installs user-level rather than into the current
   project.
2. **Add this marketplace.**
   ```
   /plugin marketplace add hengliuu/skills
   ```
   It registers as **`hengliuu`**, the name in `marketplace.json`. The install commands
   below use that name.
3. **Install the plugin.** It carries the skills, the agent roles and the hooks, and it is what loads the global context:
   ```
   /plugin install hengliuu-skills@hengliuu
   ```
4. **Verify.** Open a new session and run the check in
   [Global context](#global-context-mandatory). Skills appear namespaced, e.g.
   `hengliuu-skills:karpathy-guidelines`.

Installed plugins live in `~/.claude/plugins/`, managed by Claude Code. There is nothing
to symlink, and it works the same on macOS, Linux and Windows.

## Setup on other harnesses

opencode, Codex, Gemini CLI, Antigravity, Kiro and the rest install the skills with the
same CLI and update with one command. The only manual part is step 3, the global
context, because no other harness has a hook that can inject it.

1. **Install superpowers** (mandatory). Swap `opencode` for your harness: `codex`,
   `gemini-cli`, `antigravity`, `kiro-cli`, or `'*'` for every harness the CLI detects:
   ```
   npx skills@latest add obra/superpowers -a opencode -g
   ```
2. **Install the skills.**
   ```
   npx skills@latest add hengliuu/skills -a opencode -g
   ```
   Add
   `-s '*'` to take every skill, or `-s <name>` for a subset. **Whatever subset you pick,
   include `golden-rules`**: it carries the global context. `-a '*'` targets every
   harness the CLI detects. Skills land in `~/.agents/skills/`, and each harness gets a
   symlink to that one copy.

3. **Load the global context.** Follow your harness in
   [the next section](#load-the-global-context-per-harness). Don't skip it: without it
   the skills install, but the rules never load.
4. **Verify.** Open a new session and run the check in
   [Global context](#global-context-mandatory).
5. **New repos:** start the project's `AGENTS.md` from
   [`templates/project-level/AGENTS.md`](../templates/project-level/AGENTS.md) (`AGENTS.md.example` shows one filled in)..

The skills are plain markdown and run anywhere.

### Load the global context per harness

Every command below points at the file the skills CLI installed:

```
~/.agents/skills/golden-rules/AGENTS.md
```

Pick the row for your harness, then run the steps in its section. Where a harness
can **import** a file, import it, which keeps your own global file intact. Where it can't,
**symlink** it. Always use `ln -s`, never a plain `ln`: a hard link stops receiving
updates.

| Harness | Method | Where |
|---|---|---|
| [opencode](#opencode) | `instructions` entry in the config | `~/.config/opencode/opencode.json` |
| [Codex](#codex) | Symlink (Codex has no import) | `~/.codex/AGENTS.md` |
| [Gemini CLI](#gemini-cli-and-antigravity) | Symlink + one setting | `~/.gemini/AGENTS.md`, `~/.gemini/settings.json` |
| [Antigravity](#gemini-cli-and-antigravity) | `@` import line | `~/.gemini/GEMINI.md` (shared with Gemini CLI) |
| [Kiro](#kiro) | Symlink into the global steering folder | `~/.kiro/steering/AGENTS.md` |
| [Claude Code without the plugin](#claude-code-without-the-plugin) | `@` import line | `~/.claude/CLAUDE.md` |
| [Anything else](#anything-else) | Whatever the harness supports, paste as a last resort | N/A |

The rules file is about 3 KB, well inside every harness's size limit.

#### opencode

Add the file to `instructions` in your global config, `~/.config/opencode/opencode.json`.
Create the file if it doesn't exist:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["~/.agents/skills/golden-rules/AGENTS.md"]
}
```

If you already have an `instructions` array, add the path to it. opencode's docs show
relative paths and globs. `~` works in the current source but isn't documented. If the
check fails, write the absolute path instead (`/Users/<you>/.agents/...`, or
`/home/<you>/...` on Linux).

Don't rely on opencode's fallback to `~/.claude/CLAUDE.md`. It is skipped as soon as
`~/.config/opencode/AGENTS.md` exists, and opencode does not follow `@` imports inside it.

#### Codex

Codex reads one global file, `~/.codex/AGENTS.md` (or `$CODEX_HOME/AGENTS.md` if you set
`CODEX_HOME`), and has no import syntax. Symlink it:

```
mkdir -p ~/.codex
ln -s ~/.agents/skills/golden-rules/AGENTS.md ~/.codex/AGENTS.md
```

- **`ln: File exists`** means you already keep your own rules there. Either move them
  into your projects' `AGENTS.md` files and retry, or append the rules instead
  (`cat ~/.agents/skills/golden-rules/AGENTS.md >> ~/.codex/AGENTS.md`). Appending
  is a copy: redo it after updates.
- **An `AGENTS.override.md` in the same folder silently replaces `AGENTS.md`.** If you
  have one, the rules are not loading.

#### Gemini CLI and Antigravity

Both read the same global file, `~/.gemini/GEMINI.md`, so set this up once for both.

**Gemini CLI.** Its `@` import refuses any file outside `~/.gemini`, without an error, so
a plain import line doesn't work. Symlink the rules into that folder, then tell Gemini
CLI to read `AGENTS.md` alongside `GEMINI.md`:

```
mkdir -p ~/.gemini
ln -s ~/.agents/skills/golden-rules/AGENTS.md ~/.gemini/AGENTS.md
```

In `~/.gemini/settings.json`, merge in:

```json
{
  "context": { "fileName": ["GEMINI.md", "AGENTS.md"] }
}
```

Side effect: Gemini CLI now also reads every project's `AGENTS.md`, which is usually
what you want.

**Antigravity** reads `GEMINI.md` but not `AGENTS.md` from that folder. Add one import
line with the **absolute** path, since its docs don't mention `~`:

```
echo "@$HOME/.agents/skills/golden-rules/AGENTS.md" >> ~/.gemini/GEMINI.md
```

Gemini CLI won't follow that import (it points outside `~/.gemini`), so it doesn't load
the rules twice.

#### Kiro

Kiro always includes a file named `AGENTS.md` found in the global steering folder. It
needs no front matter:

```
mkdir -p ~/.kiro/steering
ln -s ~/.agents/skills/golden-rules/AGENTS.md ~/.kiro/steering/AGENTS.md
```

This works in the Kiro IDE and Kiro CLI, not Kiro Web. Custom Kiro agents don't load
steering on their own. They need steering listed in their `resources`, and Kiro's docs
don't say whether that pattern reaches the global folder, so run the check with the
agent you actually use.

#### Claude Code without the plugin

Only for Claude Code users who skip the `hengliuu-skills` plugin. The plugin already injects
the rules, and adding this as well loads them twice.

```
echo '@~/.agents/skills/golden-rules/AGENTS.md' >> ~/.claude/CLAUDE.md
```

#### Anything else

Check your harness's docs for a global rules file. Prefer an import, then a symlink.
**Cursor** has no global rules file: User Rules live only in *Settings → Rules*. Paste
the file's contents there, and paste again whenever `npx skills update` reports
`golden-rules`.

> [!NOTE]
> Codex, Kiro and Antigravity don't document symlinks. They read plain files, so a
> symlink should work. If the check fails with a symlink in place, replace it with a copy
> (`cp` instead of `ln -s`) and redo the copy after each update. **On Windows**,
> symlinks need Developer Mode or an admin shell, so copying is the simpler path there.

## Getting updates

| Harness | Command |
|---|---|
| Claude Code (plugins) | `/plugin marketplace update hengliuu` |
| Anything installed through the skills CLI | `npx skills@latest update -g` (`npx skills list` shows what that is) |

If you linked the global context as described above, an update reaches your sessions on
its own. If you **pasted** it instead, paste again whenever `npx skills update` lists
`golden-rules` among the skills it changed. The CLI tracks content hashes, so the
rules have no version number to watch.

## Recommended community skills

Not vendored here. Install from their upstreams. Most are on
[skills.sh](https://www.skills.sh/). All of these install with the same CLI, so they work
on whatever harness you use: add `-a <harness>` to target one other than Claude Code,
`-g` to install user-level.

| Skill | What it does | Install |
|---|---|---|
| **superpowers** | Required. Plan, brainstorm, TDD and review workflows. These skills layer on top and warn at session start if missing | `npx skills@latest add obra/superpowers -a claude-code -g` |
| **grill-me** | Adversarial interview that stress-tests a spec before it becomes a plan. Run it on the spec, then go to `writing-plans` | `npx skills@latest add mattpocock/skills --skill grill-me grilling` |
| **graphify** | Knowledge graph for everything that is **not** code: docs, papers, PDFs, images, SQL schemas, configs. Reads code too, but `graft` is the recommended default there | `pip install graphifyy && graphify install` |
| **graft** | Codebase map (optional), code only, but it wires its own Claude Code hooks and statusline. Younger and less proven. Telemetry is opt-**out**: run `graft telemetry disable` (or set `DO_NOT_TRACK=1`) before using it on private code | `npm install -g @nanonets/graft` then `graft init && graft build` |

## Troubleshooting

**The agent doesn't know the Golden Rules** (the check in
[Global context](#global-context-mandatory) fails):

1. Open a **new** session. Every harness reads its global context at session start.
2. Check the file the link points at exists:
   `ls -lL ~/.agents/skills/golden-rules/AGENTS.md`. If it doesn't:
   - You installed a subset of skills without `golden-rules`. Add it:
     `npx skills@latest add hengliuu/skills -s golden-rules -g`
   - You installed with `--copy`. That mode never creates `~/.agents/skills/`, and the file
     sits in your harness's own skills folder instead (e.g.
     `~/.codex/skills/golden-rules/AGENTS.md`). Point the link there.
3. Check your harness's own section in
   [Load the global context per harness](#load-the-global-context-per-harness). Its
   known traps are listed there: `AGENTS.override.md` for Codex, the `fileName` setting
   for Gemini CLI, the absolute path for opencode and Antigravity.

**Claude Code with the plugin, and the rules still don't load:** run `/plugin` and check
that `hengliuu-skills` is installed and enabled, then start a new session. The plugin's
SessionStart hook also warns if superpowers is missing.

**A skill warns that a skill is missing at session start** (superpowers):
install the one it names. The commands are in
[Recommended community skills](#recommended-community-skills).

**A gate stopped the agent:** that is the point. The first code edit of a session waits for
`karpathy-guidelines`, and the first merge waits for a review. Each gate fires once per
session, so the next attempt goes through. To turn all gates off, start the session with
`HENGLIUU_GATES=off`.
