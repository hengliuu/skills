# Codebase maps: graft and graphify

We support two, and the rule is the same for both: read whichever map is on disk, and
never propose a second one on top of it.

| Map | Build | Query | Refresh |
|---|---|---|---|
| `graft/` | `graft build` | `graft ask`, `graft callers`, `graft skeleton` | automatic, on every query |
| `graphify-out/` | `graphify .` | `graphify query "<q>"` | `--update`, or `--watch` |

- No map, and the work is more than a one-file change: offer to build one and let the
  user decide. Don't gate the work on it. Both extract code with tree-sitter, not a
  model, so the structural pass costs no tokens and the only real cost is wall-clock.
- The LLM layer is opt-in in both, and it is the only part that bills: `graft build
  --deep` for file summaries, graphify's INFERRED edges and report. Offer it when the
  user wants prose over structure, not by default.
- Neither is mature. Both are 0.x and ship weekly, so check which one the repo has
  instead of assuming a command exists, and don't hard-code flags into a plan.
- **Division of labour: code goes to graft, everything else goes to graphify.** Measured
  on a Python + TypeScript monorepo, not assumed. Graft answered an orientation question
  in 430 tokens against graphify's 1,534, ranked and carrying signatures, where graphify
  returned an unranked dump truncated by its own budget. Asked who calls a symbol,
  graphify answered a different question entirely.
- Docs, papers, SQL schemas, configs and images are graphify's alone. Graft indexes code
  only and silently skips every file type it doesn't parse, so it reports nothing rather
  than reporting a gap.
- **A default, not a ban.** Graphify reads code too, and remains the fallback where graft
  is blind: a language outside its 23, or a call bound through a class name
  (`Mapper.to_entity()`), which graft drops rather than guesses. Two caveats on the
  measurement — one repo, and no Go was tested.
- `graft callers` is trustworthy on module-level functions (49 of 49 on one, beating raw
  grep, which counted a comment). It is blind to class-bound calls, which is how mapper
  and repository layers are usually written. Never conclude "nothing calls this" from a
  zero: graft prints a warning saying the count may be short, and `graft grep` is the
  fallback it points at. Read the warning, not the zero.
- Neither installed: the need doesn't go away, only the tool. On a large codebase, or
  whenever the work feeds workers, say it's missing and offer the install — repeated
  Grep sweeps cost more context than one map, and their results don't transfer to
  workers at all.
