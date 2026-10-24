#!/usr/bin/env python3
"""PreToolUse gate for subagents: a large source file is read through the code map, file by file.

graft wires itself into the main session only (SessionStart and UserPromptSubmit hooks, a
project skill). A subagent gets none of that, so it reads files whole, or pages through them
with `sed -n`. This tracks, per agent and per file, how many lines of a source file the agent
has printed into its context (Read, cat, less, more, bat, nl, head, tail, sed, git show
REV:path, and `cat -n file | head -N` style paging). Once that reaches MIN_LINES of a file of
at least MIN_LINES, the read is denied until graft has named that file in this agent: a
`graft skeleton` of it, or a graft ask, callers or grep answer (CLI or MCP) that lists it.
After MAX_DENIES denials of one file the read passes, so a confused agent never loops.

Silent for the main session, for non-source and gitignored files, for edits, for output that
is redirected, captured or filtered, when graft is not installed and when the repo has no
graft index. HENGLIUU_GATES=off disables it.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

MIN_BYTES = 3000
MIN_LINES = 120
MAX_DENIES = 3
READ_DEFAULT_LIMIT = 2000
# Only what `graft skeleton` returns definitions for (checked on graft 0.23). For sh, yaml,
# toml, sql and svelte it answers "no definitions", so a deny there would be a dead end.
_SOURCE_EXT = (r"py|pyi|go|rs|ts|tsx|js|jsx|mjs|cjs|java|kt|kts|swift|rb|php|c|h|cc|cpp|hpp|cs|"
               r"scala|dart|lua|ex|exs|vue|r")
SOURCE_FILE = re.compile(rf"\.(?:{_SOURCE_EXT})$", re.I)
# Route folders such as app/(app)/[id]/page.tsx are common, so ( ) [ ] count as path characters.
_SOURCE_PATH = re.compile(rf"[\w./@~+()\[\]-]+\.(?:{_SOURCE_EXT})\b", re.I)
WHOLE_DUMPERS = {"cat", "less", "more", "nl", "bat"}
LINE_FILTERS = {"head", "tail", "sed"}
GRAFT_QUERIES = {"ask", "skeleton", "callers", "grep"}
_GRAFT_MCP = re.compile(r"mcp__.*graft.*(?:find_code|find_all|trace_calls|file_api)")
_OPERATORS = ("&&", "||", ";;", "|&", "&>>", "&>", ">&", ">>", ">|", "<<<", "<<-", "<<",
              "(", ")", ";", "&", "|", ">", "<", "\n")
_PUNCTUATION = "();<>|&\n"
_COMMAND_BREAKS = {";", ";;", "&&", "||", "&", "\n", "(", ")"}
_STDOUT_REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
_SED_RANGE = re.compile(r"(\d+)(?:,(\d+|\$))?p")
_DENIAL = "Code map first (hengliuu-skills gate)"

# A span of lines, 1-based and inclusive. A negative start counts from the end (tail -n N),
# a negative end drops lines from the end (head -n -N), and None runs to the end of the file.
# Optional rather than `int | None`: this alias is evaluated at import, and the hooks must
# run on macOS's /usr/bin/python3 (3.9).
Span = tuple[int, Optional[int]]
WHOLE: Span = (1, None)


@dataclass
class Stage:
    """One command of a pipeline: its words without redirections, and where its output goes."""

    args: list[str] = field(default_factory=list)
    redirected: bool = False
    captured: bool = False
    heredoc: bool = False


def shell_tokens(command: str) -> list[str]:
    """Words and operators. shlex glues adjacent punctuation (`)|`, `2>&1` gives `>&`), so
    runs are split back into operators. Unparseable input gives no tokens, so it passes."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=_PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        raw = list(lexer)
    except ValueError:
        return []
    tokens: list[str] = []
    for token in raw:
        if not token or any(char not in _PUNCTUATION for char in token):
            tokens.append(token)
            continue
        while token:
            operator = next((op for op in _OPERATORS if token.startswith(op)), token[0])
            tokens.append(operator)
            token = token[len(operator):]
    return tokens


def pipelines(command: str) -> Iterator[list[Stage]]:
    """Every pipeline in a shell line, each a list of stages."""
    pipeline = [Stage()]
    heredoc_end: str | None = None
    skipping = False
    depth = 0
    previous = ""
    rest = iter(shell_tokens(command))
    for token in rest:
        if skipping:  # a heredoc body is data, not commands
            if token == heredoc_end and next(rest, "\n") == "\n":
                skipping, heredoc_end = False, None
            continue
        stage = pipeline[-1]
        if token == "(" and previous.endswith("$"):
            depth += 1  # $(...) captures its output into a word
            stage.args[-1:] = [previous[:-1]] if previous[:-1] else []
        elif token == ")" and depth:
            depth -= 1
        if token == "|" or token == "|&":
            pipeline.append(Stage(captured=depth > 0))
        elif token in _COMMAND_BREAKS:
            if token == "\n" and heredoc_end is not None:
                skipping = True
            yield [stage for stage in pipeline if stage.args]
            pipeline = [Stage(captured=depth > 0)]
        elif token in _STDOUT_REDIRECTS or token in (">&", "<", "<<", "<<-", "<<<"):
            fd = stage.args.pop() if stage.args and stage.args[-1].isdigit() else "1"
            target = next(rest, "")
            to_file = token in _STDOUT_REDIRECTS or (token == ">&" and not target.isdigit())
            if to_file and (fd == "1" or token.startswith("&")):
                stage.redirected = True
            elif token == "<":
                stage.args.append(target)
            elif token in ("<<", "<<-"):
                stage.heredoc, heredoc_end = True, target.lstrip("-")
            elif token == "<<<":
                stage.heredoc = True
        else:
            stage.args.append(token)
        previous = token
    yield [stage for stage in pipeline if stage.args]


def head_tail_span(program: str, args: list[str]) -> Span | None:
    """The lines head or tail prints (10 by default), or None for a byte count."""
    count = "10"
    rest = iter(args)
    for arg in rest:
        if arg in ("-c", "--bytes") or arg.startswith(("-c", "--bytes=")):
            return None
        if arg in ("-n", "--lines"):
            count = next(rest, count)
        elif arg.startswith("--lines="):
            count = arg.split("=", 1)[1]
        elif re.fullmatch(r"-n[+-]?\d+", arg):
            count = arg[2:]
        elif re.fullmatch(r"-\d+", arg):
            count = arg[1:]
    number = int(count.lstrip("+-") or 0)
    if number == 0 and not count.startswith("+"):
        return (1, 0)
    if program == "head":
        return (1, -number) if count.startswith("-") else (1, number)
    return (number, None) if count.startswith("+") else (-number, None)


def sed_spans(args: list[str]) -> list[Span] | None:
    """Lines `sed -n 'A,Bp'` prints, WHOLE for a sed that prints every line, None for an edit."""
    short_flags = [arg for arg in args if re.match(r"-[A-Za-z]", arg)]
    if any(arg.startswith("--in-place") for arg in args) or any(re.match(r"-[A-Za-z]*i", arg) for arg in short_flags):
        return None
    quiet = any(arg in ("--quiet", "--silent") for arg in args) or any(re.fullmatch(r"-[A-Za-z]*n[A-Za-z]*", arg) for arg in short_flags)
    if not quiet:
        return [WHOLE]
    spans: list[Span] = []
    for script in (arg for arg in args if not arg.startswith("-") and not SOURCE_FILE.search(arg)):
        for start, end in _SED_RANGE.findall(script):
            spans.append((int(start), None if end == "$" else int(end or start)))
    return spans


def git_path(folder: str, flag: str) -> str:
    try:
        return subprocess.run(["git", "-C", folder, "rev-parse", flag],
                              capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def toplevel(folder: str) -> Path:
    """The repository root, or the folder itself outside a repository."""
    return Path(git_path(folder, "--show-toplevel") or folder)


def absolute(arg: str, cwd: str) -> str:
    return os.path.normpath(Path(cwd) / os.path.expanduser(arg))


def stage_reads(stage: Stage, cwd: str) -> list[tuple[str, Span]]:
    """(path, span) for each source file one command prints on its own."""
    program, args = Path(stage.args[0]).name, stage.args[1:]
    if stage.heredoc:
        return []
    if program == "git" and args[:1] == ["show"]:
        return [(os.path.normpath(toplevel(cwd) / arg.split(":", 1)[1]), WHOLE)
                for arg in args[1:] if ":" in arg and SOURCE_FILE.search(arg)]
    spans: list[Span] | None
    if program in WHOLE_DUMPERS:
        line_range = next((args[i + 1] for i, arg in enumerate(args[:-1]) if arg in ("-r", "--line-range")), "")
        bounds = re.fullmatch(r"(\d+):(\d+)", line_range) if program == "bat" else None
        spans = [(int(bounds.group(1)), int(bounds.group(2)))] if bounds else [WHOLE]
    elif program in ("head", "tail"):
        span = head_tail_span(program, args)
        spans = [span] if span else None
    elif program == "sed":
        spans = sed_spans(args)
    else:
        return []
    files = [absolute(arg, cwd) for arg in args if not arg.startswith("-") and SOURCE_FILE.search(arg)]
    return [(path, span) for path in files for span in spans or []]


def filter_spans(stage: Stage) -> list[Span] | None:
    """Lines a head, tail or sed stage lets through from its input, or None if it is not one."""
    program, args = Path(stage.args[0]).name, stage.args[1:]
    if program not in LINE_FILTERS or any(SOURCE_FILE.search(arg) for arg in args):
        return None
    if program == "sed":
        return sed_spans(args)
    span = head_tail_span(program, args)
    return [span] if span else None


def bash_reads(command: str, cwd: str) -> list[tuple[str, Span]]:
    """(absolute path, span) for each source file a command prints into the agent's context."""
    reads: list[tuple[str, Span]] = []
    for pipeline in pipelines(command):
        if not pipeline:
            continue
        first, last = pipeline[0], pipeline[-1]
        if len(pipeline) == 1 and Path(first.args[0]).name == "cd" and len(first.args) == 2:
            cwd = absolute(first.args[1], cwd)
            continue
        if last.redirected or last.captured:
            continue
        if len(pipeline) == 1:
            reads += stage_reads(first, cwd)
        elif len(pipeline) == 2:  # cat -n f | head -300, git show REV:f | sed -n 1,200p
            source = stage_reads(first, cwd)
            spans = filter_spans(last)
            if spans and len(source) == 1 and source[0][1] == WHOLE:
                reads += [(source[0][0], span) for span in spans]
    return reads


def read_tool_span(args: dict[str, object]) -> Span:
    start = max(int(str(args.get("offset") or 1)), 1)
    return (start, start + int(str(args.get("limit") or READ_DEFAULT_LIMIT)) - 1)


def line_count(path: str) -> int:
    """Lines in a source file worth gating, or 0 for a small, missing or unreadable one."""
    try:
        if Path(path).stat().st_size < MIN_BYTES:
            return 0
        with open(path, "rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def span_lines(span: Span, total: int) -> int:
    start, end = span
    first = total + start + 1 if start < 0 else start
    last = total if end is None else total + end if end < 0 else min(end, total)
    return max(last - max(first, 1) + 1, 0)


def index_roots(folder: Path) -> list[Path]:
    """Folders holding a graft index or workspace above `folder`, then the main checkout's when
    `folder` is in a worktree, nearest first."""
    candidates = [folder, *folder.parents]
    common = git_path(str(folder), "--git-common-dir")
    if common:
        main = (folder / common).resolve().parent
        candidates += [main, *main.parents]
    return [root for root in candidates
            if (root / "graft" / "INDEX.md").is_file() or (root / "graft" / "workspace.json").is_file()]


def is_ignored(path: str) -> bool:
    try:
        return subprocess.run(["git", "-C", str(Path(path).parent), "check-ignore", "-q", path],
                              capture_output=True, timeout=3).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def is_graft_query(args: list[str]) -> bool:
    return Path(args[0]).name in ("graft", "trail") and len(args) > 1 and args[1] in GRAFT_QUERIES


def agent_transcript(payload: dict[str, object], agent: str) -> Path | None:
    """The agent's own transcript: <session>/subagents/agent-<id>.jsonl beside the main one."""
    raw = str(payload.get("agent_transcript_path") or payload.get("transcript_path") or "")
    if not raw:
        return None
    main = Path(raw)
    if main.name == f"agent-{agent}.jsonl":
        return main
    candidate = main.with_suffix("") / "subagents" / f"agent-{agent}.jsonl"
    return candidate if candidate.is_file() else None


def result_text(content: object) -> str:
    if isinstance(content, str):
        return content
    parts = content if isinstance(content, list) else []
    return "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))


def skeleton_targets(args: list[str], cwd: str) -> list[str]:
    """Absolute paths a `graft skeleton <file> [dir]` call names."""
    positional = [arg for arg in args[2:] if not arg.startswith("-")]
    if args[1] != "skeleton" or not positional:
        return []
    base = absolute(positional[1], cwd) if len(positional) > 1 else cwd
    return [absolute(positional[0], base)]


@dataclass
class GraftEvidence:
    """What graft told this agent: the files its skeleton calls named and the text it returned."""

    files: set[str] = field(default_factory=set)
    text: str = ""

    def names(self, target: str) -> bool:
        if target in self.files:
            return True
        folder = Path(target).parent
        relatives = {os.path.relpath(target, root) for root in [toplevel(str(folder)), *index_roots(folder)]}
        for mention in _SOURCE_PATH.findall(self.text):
            mention = mention.lstrip("([").removeprefix("./")
            if mention == target or mention in relatives:
                return True
        return False


def record_graft_calls(command: str, cwd: str, evidence: GraftEvidence) -> bool:
    """Add the files a command's graft skeleton calls name. True if it ran any graft query."""
    ran = False
    for pipeline in pipelines(command):
        if len(pipeline) == 1 and Path(pipeline[0].args[0]).name == "cd" and len(pipeline[0].args) == 2:
            cwd = absolute(pipeline[0].args[1], cwd)
            continue
        for stage in pipeline:
            if is_graft_query(stage.args):
                ran = True
                evidence.files.update(skeleton_targets(stage.args, cwd))
    return ran


def graft_evidence(transcript: Path | None, cwd: str) -> GraftEvidence:
    evidence = GraftEvidence()
    if transcript is None:
        return evidence
    texts: list[str] = []
    graft_ids: set[str] = set()
    try:
        handle = open(transcript, encoding="utf-8", errors="ignore")
    except OSError:
        return evidence
    with handle:
        for line in handle:
            if "graft" not in line and not graft_ids:
                continue
            try:
                content = (json.loads(line).get("message") or {}).get("content")
            except ValueError:
                continue
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    name, args = str(block.get("name", "")), block.get("input") or {}
                    if _GRAFT_MCP.match(name):
                        graft_ids.add(str(block.get("id")))
                        texts.append(json.dumps(args))
                    elif name == "Bash" and record_graft_calls(str(args.get("command", "")), cwd, evidence):
                        graft_ids.add(str(block.get("id")))
                elif block.get("type") == "tool_result" and block.get("tool_use_id") in graft_ids:
                    texts.append(result_text(block.get("content")))
    evidence.text = "\n".join(texts)
    return evidence


class AgentState:
    """Lines read and denials per file for one agent, kept in a temp file between hook calls."""

    def __init__(self, key: str) -> None:
        safe_key = re.sub(r"[^\w-]", "_", key)
        self.path = Path(tempfile.gettempdir()) / "hengliuu-skills-gates" / f"{safe_key}.map.json"
        try:
            self.files: dict[str, dict[str, int]] = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.files = {}

    def entry(self, target: str) -> dict[str, int]:
        return self.files.setdefault(target, {"lines": 0, "denied": 0})

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.files))
            return True
        except OSError:
            return False


def deny_message(target: str, total: int, index: Path) -> str:
    top = git_path(str(Path(target).parent), "--show-toplevel")
    root = Path(top) if top else index
    relative = os.path.relpath(target, root)
    # graft looks for its index from the folder it runs in, not from the file, and an absolute
    # file path finds no definitions. A path relative to the root plus the root as [dir] works
    # from any folder, including the session folder a subagent's shell starts in.
    question = '"<question>"'
    return (f"{_DENIAL}: {relative} has {total} lines and graft has not named it in this agent. "
            f"Run `graft skeleton {relative} {root}` for its API with line spans, or "
            f"`graft ask {question} --source {root}`, then read only the ranges it returns. "
            f"Reads of this file pass once graft has named it.")


def main() -> None:
    if os.environ.get("HENGLIUU_GATES", "").lower() in ("off", "0", "false"):
        return
    payload = json.load(sys.stdin)
    agent = str(payload.get("agent_id") or "")
    if not agent:
        return
    tool, args = str(payload.get("tool_name", "")), payload.get("tool_input") or {}
    cwd = str(payload.get("cwd") or os.getcwd())
    command = str(args.get("command", "")) if tool == "Bash" else ""

    if tool == "Read":
        reads = [(str(args.get("file_path", "")), read_tool_span(args))]
    elif command:
        reads = bash_reads(command, cwd)
    else:
        return
    files: dict[str, tuple[int, int]] = {}
    for target, span in reads:
        total = line_count(target) if SOURCE_FILE.search(target) else 0
        if total >= MIN_LINES:
            files[target] = (total, files.get(target, (total, 0))[1] + span_lines(span, total))
    if not files:
        return

    state = AgentState(f"{payload.get('session_id', '')}-{agent}")
    evidence: GraftEvidence | None = None
    for target, (total, lines) in files.items():
        entry = state.entry(target)
        if entry["lines"] + lines < MIN_LINES or entry["denied"] >= MAX_DENIES:
            continue
        if evidence is None:
            evidence = graft_evidence(agent_transcript(payload, agent), cwd)
        if evidence.names(target) or is_ignored(target):
            continue
        roots = index_roots(Path(target).parent)
        if not (shutil.which("graft") or shutil.which("trail")) or not roots:
            return  # no code map to send the agent to, so neither gate nor count
        entry["denied"] += 1
        if state.save():  # without saved state the gate could not stop denying, so never block
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": deny_message(target, total, roots[0]),
            }}))
        return
    for target, (_, lines) in files.items():
        state.entry(target)["lines"] += lines
    state.save()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a broken gate must never block work
        pass
