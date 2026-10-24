#!/usr/bin/env bash
# SessionStart: nudge for a codebase map when the repo is code and has none.
#
# Deliberately tool-agnostic. graft and graphify both extract code with tree-sitter and
# both are 0.x shipping weekly, so the playbook names the behaviour (read a map, don't
# bulk-read) and this hook only reports which map, if any, is on disk. Neither is
# vendored: both ship their own wiring — graft writes Claude Code hooks and a statusline
# via `graft init`, graphify installs a post-commit rebuild hook — which a copy strips.
#
# Two checks, both silent unless they have something to say:
#   1. graft's telemetry, which is opt-OUT: a plain npm install on a laptop sends
#      anonymous usage events until someone turns it off. Client repos want zero.
#   2. a missing codebase map.
# Skipped entirely in a non-code repo (docs, skills, config). Check 2 also exits
# once a map exists — the tool owns freshness from there.
#
# Never exits non-zero: neither a missing map nor telemetry may block a session.

set -uo pipefail

# Cheap, deterministic gate: a build manifest is what makes a directory a code repo.
# Cheaper and less noisy than walking the tree for source extensions.
is_code_repo() {
  local m
  for m in package.json go.mod pyproject.toml requirements.txt Cargo.toml pom.xml \
           build.gradle build.gradle.kts Gemfile composer.json mix.exs Package.swift; do
    [ -f "$m" ] && return 0
  done
  compgen -G "*.csproj" >/dev/null 2>&1 && return 0
  compgen -G "*.sln" >/dev/null 2>&1 && return 0
  return 1
}

is_code_repo || exit 0

# --- check 1: graft telemetry -----------------------------------------------
# Read ~/.graft/telemetry.json directly rather than shelling out to `graft
# telemetry`: this runs on every session start, and a process spawn costs more
# than the check is worth. Mirror graft's own gate so we never warn about
# something already off — it disables itself in CI and honours DO_NOT_TRACK.
in_ci() {
  case "${CI:-}" in "" | 0 | false) ;; *) return 0 ;; esac
  [ -n "${GITHUB_ACTIONS:-}${GITLAB_CI:-}${BUILDKITE:-}${CIRCLECI:-}" ] && return 0
  [ -n "${TEAMCITY_VERSION:-}${JENKINS_URL:-}${TF_BUILD:-}${BUILD_NUMBER:-}" ] && return 0
  return 1
}

telemetry_on() {
  command -v graft >/dev/null 2>&1 || return 1
  case "${DO_NOT_TRACK:-}" in "" | 0) ;; *) return 1 ;; esac
  in_ci && return 1
  # No state file means never disabled, and graft defaults to on.
  local state="$HOME/.graft/telemetry.json"
  [ -f "$state" ] && grep -q '"enabled"[[:space:]]*:[[:space:]]*false' "$state" && return 1
  return 0
}

if telemetry_on; then
  printf '\n⚠️  graft telemetry is ON (it is opt-out, so a plain install sends by default).\n'
  printf 'Events are anonymous — os, languages, bucketed file counts, a random UUID; no\n'
  printf 'repo name, path or code — but they go to a third party, so a client repo wants\n'
  printf 'zero. Tell the user to run once:\n\n'
  printf '  graft telemetry disable\n\n'
  printf 'Team-wide, DO_NOT_TRACK=1 in the shell profile covers it without anyone having\n'
  printf 'to remember. graft already disables itself in CI.\n'
fi

# --- check 2: codebase map --------------------------------------------------
[ -d "graft" ] && exit 0
[ -d "graphify-out" ] && exit 0

have_graft=0; have_graphify=0
command -v graft     >/dev/null 2>&1 && have_graft=1
command -v graphify  >/dev/null 2>&1 && have_graphify=1

printf '\n📍 hengliuu-skills: this is a code repo with no codebase map (no graft/, no graphify-out/).\n'

if [ "$have_graft" = 1 ] || [ "$have_graphify" = 1 ]; then
  printf 'Offer to build one before work that spans more than one file. Code extraction is\n'
  printf 'tree-sitter in both tools, so the structural pass costs no model tokens. Available:\n'
  [ "$have_graft" = 1 ]    && printf '  graft build          # then: graft ask / graft callers / graft skeleton\n'
  [ "$have_graphify" = 1 ] && printf '  graphify .           # then: graphify query "<question>"\n'
  printf 'Add the LLM layer (graft --deep, graphify inferred edges) only if the user asks for\n'
  printf 'prose over structure — that is the part that bills. Soft gate: the user decides.\n'
  exit 0
fi

printf 'Neither map tool is installed. Both are optional; on anything bigger than a few\n'
printf 'files a map is cheaper than repeated Grep sweeps, and Grep results do not transfer\n'
printf 'to subagents at all. Tell the user to pick one:\n\n'
printf '  npm install -g @nanonets/graft && graft init && graft build\n'
printf '      code only, wires its own Claude Code hooks + statusline\n'
printf '  pip install graphifyy && graphify install\n'
printf '      also ingests docs, PDFs and images; far more widely deployed\n\n'
printf 'Until then, do NOT bulk-read the codebase — aim Grep at the directories the task\n'
printf 'actually touches, and say the map is missing.\n'
exit 0
