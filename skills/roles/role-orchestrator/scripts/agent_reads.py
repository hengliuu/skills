#!/usr/bin/env python3
"""Per-agent read report for a Claude Code session: did the agents read code through graft?

Reads the subagent transcripts Claude Code keeps beside a session
(~/.claude/projects/<project>/<session>/subagents/agent-*.jsonl) and prints, per agent, its
tool calls, graft calls, source reads (Read, cat, sed, head, tail, nl, less, bat, git show
of a source file), the characters each kind returned, the map-gate denials it hit and the
named agents it spawned.

    agent_reads.py                 newest session of the project in the current folder
    agent_reads.py <session-id>    that session of the current project
    agent_reads.py <path>          a session folder or its .jsonl transcript
    agent_reads.py ... --json      one JSON object per agent instead of a table
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
_SOURCE = (r"py|pyi|go|rs|ts|tsx|js|jsx|mjs|cjs|java|kt|kts|swift|rb|php|c|h|cc|cpp|hpp|cs|"
           r"scala|dart|lua|ex|exs|vue|r")
SOURCE_FILE = re.compile(rf"\.(?:{_SOURCE})$", re.I)
_SHELL_READ = re.compile(
    rf"(?:^|[;&|(]\s*)(?:cat|sed|head|tail|nl|less|more|bat|git\s+show)\b[^;&|\n]*\.(?:{_SOURCE})\b", re.I)
_GRAFT_CLI = re.compile(r"(?:^|[;&|(]\s*)(?:graft|trail)\s+(?:ask|skeleton|callers|grep|map)\b")
# How Claude Code records a hook's deny: an error result naming the hook. Matching the prefix keeps
# an agent that merely read map_gate.py, or an AGENTS.md line, out of the count.
_GATE_DENIAL = re.compile(r"^(?:Error: )?PreToolUse:\w+ hook error: Code map first \(hengliuu-skills gate")
_SED_IN_PLACE = re.compile(r"\bsed\b[^;&|\n]*\s-[A-Za-z]*i")


@dataclass
class AgentReads:
    agent: str
    role: str
    calls: int = 0
    graft_calls: int = 0
    source_reads: int = 0
    source_chars: int = 0
    graft_chars: int = 0
    output_chars: int = 0
    gate_denials: int = 0
    named_spawns: int = 0


def kind_of(name: str, args: dict[str, object]) -> str:
    command = str(args.get("command", "")) if name == "Bash" else ""
    if re.match(r"mcp__.*graft", name) or _GRAFT_CLI.search(command):
        return "graft"
    if name == "Read" and SOURCE_FILE.search(str(args.get("file_path", ""))):
        return "source"
    if _SHELL_READ.search(command) and not _SED_IN_PLACE.search(command):
        return "source"
    return "other"


def result_text(content: object) -> str:
    """The text a tool returned. Images are left out: they arrive as base64, and their cost
    is not their length."""
    if isinstance(content, str):
        return content
    parts = content if isinstance(content, list) else []
    return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("type") == "text")


def scan(transcript: Path) -> AgentReads:
    meta_file = transcript.with_name(transcript.name.removesuffix(".jsonl") + ".meta.json")
    try:
        meta = json.loads(meta_file.read_text())
    except (OSError, ValueError):
        meta = {}
    row = AgentReads(agent=str(meta.get("description") or transcript.stem)[:40],
                     role=str(meta.get("spawnedAgentType") or meta.get("agentType") or "?"))
    kinds: dict[str, str] = {}
    with transcript.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                content = (json.loads(line).get("message") or {}).get("content")
            except ValueError:
                continue
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    name, args = str(block.get("name", "")), block.get("input") or {}
                    kinds[str(block.get("id"))] = kind = kind_of(name, args)
                    row.calls += 1
                    row.graft_calls += kind == "graft"
                    row.source_reads += kind == "source"
                    row.named_spawns += name in ("Agent", "Task") and bool(args.get("name"))
                elif block.get("type") == "tool_result":
                    text = result_text(block.get("content"))
                    kind = kinds.get(str(block.get("tool_use_id")), "other")
                    row.output_chars += len(text)
                    row.source_chars += len(text) if kind == "source" else 0
                    row.graft_chars += len(text) if kind == "graft" else 0
                    row.gate_denials += bool(block.get("is_error") and _GATE_DENIAL.match(text))
    return row


def session_dir(argument: str | None) -> Path:
    if argument and Path(argument).exists():
        path = Path(argument)
        return path.with_suffix("") if path.suffix == ".jsonl" else path
    project = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    if argument:
        return project / argument
    sessions = [folder for folder in project.glob("*/subagents") if folder.is_dir()]
    if not sessions:
        raise SystemExit(f"no session with subagents under {project}")
    return max(sessions, key=lambda folder: folder.stat().st_mtime).parent


def render(rows: list[AgentReads]) -> str:
    header = f"{'agent':40} {'role':24} {'calls':>5} {'graft':>5} {'reads':>5} {'read %':>6} {'graft k':>7} {'denied':>6} {'named':>5}"
    lines = [header, "-" * len(header)]
    for row in rows:
        share = 100 * row.source_chars // row.output_chars if row.output_chars else 0
        lines.append(f"{row.agent:40} {row.role[:24]:24} {row.calls:5} {row.graft_calls:5} {row.source_reads:5} "
                     f"{share:5}% {row.graft_chars // 1000:7} {row.gate_denials:6} {row.named_spawns:5}")
    lines.append("read % = share of the agent's text tool output (images left out) that came from source reads. "
                 "graft k = thousands of characters graft returned.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    positional = [arg for arg in argv if arg != "--json"]
    folder = session_dir(positional[0] if positional else None) / "subagents"
    rows = [scan(path) for path in sorted(folder.glob("agent-*.jsonl"), key=lambda p: p.stat().st_mtime)]
    if as_json:
        print("\n".join(json.dumps(asdict(row)) for row in rows))
    else:
        print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
