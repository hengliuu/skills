# Jev setup and operations

Jev is TypeSafe's fast judgment model. It answers yes/no, pick-one and score questions in about a
second, returns numbers rather than prose, and never writes anything. The `jev` skill works on any
harness that can run Python 3. The three hooks below need Claude Code, because hooks do not travel
through the skills CLI. Jev is optional: nothing else in this plugin depends on it.

## What runs, and when

The hooks send text to TypeSafe, so they run **only in folders you allow** (see [Set up](#set-up)).
Everywhere else they do nothing.

| Piece | Runs | Sends to TypeSafe | Does |
|---|---|---|---|
| `check-jev.sh` | Session start | One synthetic question (`n = 7?`), never repo content | Says whether the key works and the folder is allowed |
| Skill router | Every prompt of 12+ characters that does not start with `/` | The prompt, cut at 4,000 characters | Suggests the skills the prompt calls for |
| Unverified-done check | End of a turn that edited files other than `.md`, `.mdx` or `.txt` | Edited file names, up to 25 commands (300 characters each), the final message (4,000 characters) | Blocks a "done" that no command verified, once, then lets it through |
| `jev` skill | When invoked | What the request file contains | Batch judgments and decision points |
| `jev.py route` | When run, before dispatching a plan, only if the plan's repo root is allowed | Each task's text, files and check from the plan's task table | A second pick of role and effort per task, the model that role runs on, and a verdict (sure, close, check the effort, UNSURE) |
| `jev.py gate` | When run, before a review, only if the repo root is allowed | The request text, each changed hunk with 3 lines of context, each added comment, the enclosing function of a changed loop, and new untracked (not gitignored) files. At most 6,000 characters per item, 80 items per run | Scope, Comments and Algorithm gates: lists hunks that may be scope creep, comments that restate code, and repeated linear scans |

Each hook makes one attempt and fails open. If Jev is unreachable, the prompt or stop goes through
unchanged.

## Set up

Do this once, yourself. The key is personal, and choosing which folders may send text to a cloud API
is a decision only the person who owns them can make.

1. Install the plugin: `/plugin install hengliuu-skills@hengliuu`. A skills-CLI install has the
   skill and its scripts but no hooks.
2. Run the guided setup in a terminal, not inside Claude Code, because the key prompt needs a real
   terminal:

   ```bash
   JEV=$(ls -d ~/.claude/plugins/cache/hengliuu/hengliuu-skills/*/skills/engineering/jev/scripts/jev.py | sort -V | tail -1)
   python3 "$JEV" setup
   ```

   It stores the key if none is found, asks which folders to allow, then tests the key. Replace a
   stale key with `python3 "$JEV" key`. Add or list folders later with `python3 "$JEV" allow FOLDER`
   and `python3 "$JEV" allowed`. Subfolders of an allowed folder count. Your home folder and the drive
   root are refused as too broad.
3. Open a new Claude Code session in an allowed folder. `check-jev.sh` stays silent when all is well.

A key needs a TypeSafe account. Check TypeSafe's own pages for how keys are issued, because access
terms have changed more than once.

### Where the key lives

The lookup order is the same on every OS. Hooks do not inherit your login shell, so a stored key is
more reliable than an exported variable.

| Source | Used | Notes |
|---|---|---|
| `TYPESAFE_API_KEY` in the environment | First | Overrides anything stored. Must be exported where Claude Code starts |
| `~/.claude/jev/key` | Second | Written by `setup` and `key` on Linux and Windows. Plain text, mode 600 where the OS supports it |
| macOS Keychain (service `TYPESAFE_API_KEY`) | Third | Written by `setup` and `key` on macOS. macOS asks for the key twice and shows nothing you type |

### macOS

Verified on this plugin at 1.6.0 on 2026-11-07, run from the installed plugin folder: the key check
against the real TypeSafe endpoint, the router logging in an allowed folder and silent outside it,
the done-check blocking an unverified claim, the session-start check silent, and the router on
macOS's own `/usr/bin/python3` (3.9). Without `setup`:

```bash
security add-generic-password -U -a "$USER" -s TYPESAFE_API_KEY -w   # prompts, never enters a transcript
mkdir -p ~/.claude/jev && echo '{"hooks_allow": ["~/code/some-repo"]}' > ~/.claude/jev/config.json   # creates the file, skip it if you already have one
python3 "$JEV" --check
```

### Linux

Verified, on the standalone version this skill came from and not yet on this plugin's layout, in a Debian 13 container (Python 3.12, `sh` is dash): the unit tests, the hook commands
including the `python3` to `python` fallback, `setup`, `key`, `allow`, and the session-start check
against the real TypeSafe endpoint. Not verified on other distributions, or with Claude Code launched
from a desktop icon, which may not see variables from your shell profile. Use the key file there.

### Windows

**Not verified.** The known blockers were removed: the hooks fall back from `python3` to `python`,
the key lookup works without a Keychain, and the repo's `.gitattributes` keeps `.sh` files on LF.
Nobody has run it on Windows yet. What it needs:

- Python 3 with `python` on `PATH`, and a POSIX shell such as Git Bash. The hooks are shell commands,
  and this plugin's other hooks need one too.
- `setup` and `key` write `%USERPROFILE%\.claude\jev\key`. It is plain text, and its protection is
  your profile's default permissions. An exported `TYPESAFE_API_KEY` also works
  (`setx TYPESAFE_API_KEY "<your key>"`, then restart Claude Code).
- Entries in `config.json` written as `~/code/some-repo` or with forward slashes.
- If a hook fails with `\r: command not found`, a script was checked out with CRLF. Check
  `git config core.autocrlf` and reinstall the plugin.

To verify it, run these steps and report the first one that fails, with its error text:

1. From the shell Claude Code uses, `python --version` and `bash --version` both work.
2. `/plugin install hengliuu-skills@hengliuu`, then restart Claude Code.
3. Run `python <plugin folder>\skills\engineering\jev\scripts\jev.py setup`. The plugin folder is
   under `%USERPROFILE%\.claude\plugins\cache\hengliuu\hengliuu-skills\`.
4. In a new session in an allowed folder, send one prompt of 12+ characters. A new line appears in
   `%USERPROFILE%\.claude\jev\hooks.log.jsonl`.
5. In a folder outside `hooks_allow`, send a prompt. Nothing is appended.
6. Start a session with a wrong key in `key`. The session-start check names the 401 and the fix.

## Configuration

`~/.claude/jev/config.json` is yours, and only `setup` and `allow` write it. It sits on top of the
skill's `config.default.json`.

| Key | Meaning | Default |
|---|---|---|
| `hooks_allow` | Folders where the hooks may run. Never taken from the defaults | `[]`, so off everywhere |
| `router_skills` | `{"skill-name": "when the prompt calls for it"}`. A `null` value drops a default | This plugin's skills and superpowers |
| `router_threshold` | Minimum score for the router to suggest a skill | `0.7` |
| `stop_threshold` | Minimum score for the done-check to block | `0.8` |
| `model` | Jev model for the hooks, the skill, `gate` and `route`: `jev-preview` to try the next version, or a pinned one such as `jev-1.13.0` | `jev-latest` |

The router only suggests skills you list, so add the stack and creative skills you use, for example
`"my-plugin:python-conventions": "The prompt asks to write or change Python code."`.

`~/.claude/jev/hooks.log.jsonl` records the hook, its score, the model and latency, never any text.
Read it to tune the thresholds. Its modification time is the quickest sign that the hooks ran.

## Troubleshooting

`$JEV` is the variable from step 2 of [Set up](#set-up).

| Session-start message | Cause | Fix |
|---|---|---|
| `no folder is allowlisted` | `hooks_allow` is missing or empty | `python3 "$JEV" allow FOLDER` |
| `Jev has no API key` | No key in the environment, the key file or the Keychain | `python3 "$JEV" key` |
| `Jev rejected the stored API key (401)` | The key is stale, or a wrong `TYPESAFE_API_KEY` in the shell overrides the stored one | `python3 "$JEV" key`, or unset the variable. `--check` says where the key came from |
| `could not answer` | TypeSafe unreachable | The hooks fail open, so retry later |
| Nothing at all | Healthy, or the folder is outside a non-empty `hooks_allow` (on purpose, no message) | `python3 "$JEV" allowed` |

## Uninstall

Remove the hooks by uninstalling the plugin: `/plugin uninstall hengliuu-skills@hengliuu`. Your config
and log stay in `~/.claude/jev/`.

## Developing

`python3 -m unittest discover -s skills/engineering/jev/tests` runs offline, because every Jev call
is faked. This plugin's hooks must also run on macOS's own `/usr/bin/python3` (3.9), so run the same
command with that interpreter after any change.
