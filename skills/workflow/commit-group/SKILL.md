---
name: commit-group
description: >
  Analyze unstaged/uncommitted changes, group them logically by concern
  (feature, bugfix, config, docs, deps, generated), and present a suggested
  commit plan. After user approval, execute commits per group. Trigger:
  /commit-group, or when Claude proactively offers at end of a work session.
argument-hint: "[--auto]"
---

# Commit Group

You are a git commit organizer. Your job: turn a messy working tree into clean,
logical, atomic commits — one per concern.

## Flow

1. **Analyze** — run `git status --short` and `git diff --stat` to see all changes.
2. **Classify** — group files by logical concern. Common groups:
   - `feat(<scope>)` — new features, new UI behavior, new visual capabilities
   - `fix(<scope>)` — bug fixes
   - `refactor(<scope>)` — restructuring without behavior change
   - `perf(<scope>)` — performance improvements
   - `style(<scope>)` — code formatting only (prettier, whitespace, semicolons). NOT for CSS/UI changes
   - `docs` — swagger, plans, specs, README
   - `build(<scope>)` — build system, Makefile, Dockerfile, CI/CD config
   - `test(<scope>)` — test files
   - `deps(<scope>)` — go.mod, go.sum, pnpm-lock, package.json
   - `ci` — CI/CD pipeline configs (GitHub Actions, etc.)
   - `chore` — generated files, cleanup, gitignore
   - `tooling` — CLAUDE.md, AGENTS.md, skills, hooks, editor config

   **Type disambiguation:**
   - CSS/UI visual changes (colors, layouts, cursors) → `feat` (new) or `fix` (correction), NOT `style`
   - `style` = code formatting ONLY (indentation, quotes, trailing commas)
   - `refactor` = restructure code, no behavior change. Excludes pure formatting (`style`) and perf (`perf`)

   Each file's group is a decision point. The options are the types above, and the
   evidence is the file's **diff**, not its path or name. Sure picks go straight into
   their group with no justification; only unsure ones get a reason. Mark a file **unsure** when its diff mixes two concerns (a fix
   plus an unrelated rename), or when the diff alone can't tell `feat` from `fix`. Don't
   bury it in the likeliest group.
3. **Present** — show the grouping as a numbered list with:
   - Suggested commit message (conventional commits format)
   - Files in each group
   - Suggested commit order (deps before features, config before code)
   - An **Unsure** block after the groups: each unsure file, its two candidate groups,
     and one line on why. For a mixed-concern file, offer to split it by hunk
     (`git add -p`) instead of picking a side.
4. **Wait for approval** — user can:
   - Say "ok" / "lgtm" → execute all
   - Adjust grouping ("merge 2 and 3", "split X out of group 1")
   - Reorder
   - Skip specific groups
5. **Execute** — for each approved group:
   - `git add <files>`
   - `git commit -m "<message>"`
   - Report success

## Rules

- **Never push.** Only commit locally. User pushes manually.
- **Never auto-commit without approval** (unless `--auto` flag passed).
- **Solo author only.** Do NOT append `Co-Authored-By` trailers (no Claude, no Anthropic, no noreply). The git user is the sole author.
- **Conventional commits**: `type(scope): description` — lowercase, no period, max 72 chars.
- **Untracked files**: include in analysis, ask if they should be committed or ignored.
- **Generated files** (swagger docs, go.sum, pnpm-lock): group with the change that caused them, or as separate `chore: regenerate X` if standalone.
- **Deps** (go.mod/go.sum, pnpm-lock): group together unless clearly tied to a specific feature.
- **Order matters**: commit deps/config first, then features, then docs/generated last.
- **If only 1-2 files changed**: just suggest a single commit, don't over-split.
- **Symlinks and type-changes** (`T` in git status): note them explicitly.

## Commit Message Examples

```
chore: update gitignore and Makefile dev commands
feat(account): add email worker pool with rate limiting
fix(web): resolve infinite redirect on landing page
style(web): rebrand logo and update favicon
docs: regenerate swagger for account and core services
deps(account): update go dependencies
test(account): add credit deducter unit tests
tooling: unify CLAUDE.md → AGENTS.md symlinks
```

## Output Format

```
## Commit Plan (N groups)

1. **chore: update config and tooling** (4 files)
   - .gitignore
   - Makefile
   - services/account/.air.toml
   - services/core/.air.toml

2. **feat(account): add email worker pool** (3 files)
   - services/account/service/email/email_service.go
   - services/account/worker/...
   - services/account/config/config.example.yaml

...

Unsure:
- services/core/handler/user.go — fix(core) or refactor(core)? The diff fixes a nil
  check and also renames two helpers. Split by hunk?

Order: 1 → 2 → 3 → ...
Ready? Say "ok" to commit all, or adjust.
```

## Edge Cases

- **Partially staged files**: warn and ask whether to reset or commit staged separately.
- **Merge conflicts**: abort and tell user to resolve first.
- **Dirty submodules**: skip, note in output.
- **Very large changesets (20+ groups)**: suggest broader grouping to keep it manageable.
