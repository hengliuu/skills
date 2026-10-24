---
name: intent-capture
description: >
  Turn a request into a committed intent.md — the record of what was asked and why,
  written before anyone designs a solution. Use this whenever work arrives from someone
  other than the person doing it: a client ask, a stakeholder complaint, meeting notes
  or MoM to write up, "klien minta X", "bikin intent", "catat requirement ini", "ini
  hasil meeting tadi", or a monitoring alert that should become new work. Use it BEFORE
  the brainstorming skill on any client or stakeholder work — brainstorming decides the
  solution, this records the problem that justified having one. Also use when asked to
  review or sharpen an existing intent file.
---

# Intent capture

Stage 1 of the AI-native SDLC: the requester tells the story, you write the file, the
requester corrects it. The result is committed to git next to the code, so six months
later the question "why did we build this at all?" has an answer that isn't a chat log.

## The one rule

**Capture the ask, not the answer.** An intent file that names a technology, a screen,
an endpoint, or a vendor has skipped ahead — it locks in a solution before anyone
checked whether a cheaper one exists. If the requester says "we need a WhatsApp blast",
that is your starting point, not your content: walk them back to what breaks without it.

The practical test: **could someone who cannot code have written this?** If it needed an
engineer, you have written a spec, and it belongs in the design stage instead.

## When to skip this

When the requester and the implementer are the same person, this is ceremony. Bugfixes,
internal refactors, an endpoint you decided to add — go straight to `brainstorming`.

The file earns its keep when someone else is asking: a client, a PM, an ops lead. That
is the case where "I never asked for that" costs real money, and where the requester
needs something to approve before work starts.

## The interview

Read what you were given first — meeting notes, a chat dump, a voice memo transcript,
a spoken story. Most of it is context you can discard; you are looking for one problem
and the conditions around it.

Then ask about the gaps, **one question at a time**. Transcribing what you were handed
produces a tidier MoM and nothing more — the value is in the four things people almost
never volunteer:

**1. The problem as impact, not as a request.** People arrive with a solution already
attached ("we need notifications"). Walk it back: what happens today that shouldn't?
how often? who absorbs the cost? Push until there is something countable — "40 calls a
day, 3 hours of CS time". That number is what a later stage measures success against,
and no one can reconstruct it afterwards. Then ask where it can be read again six
months from now — which export, which dashboard, whose report. A number nobody can pull
a second time never gets checked.

**2. Constraints.** Nobody offers these unprompted. Ask directly: what data must not
leave the system? what budget exists this quarter? what has already been promised to
the client, and by when? which systems are off limits? A constraint discovered during
implementation is a rewrite; discovered here it is one sentence.

**3. Risks.** Not the same as a constraint: a constraint is a wall you build around, a
risk is something that may or may not happen and would hurt if it did — a vendor that
might not deliver, a regulation mid-revision, a peak season the launch lands on. Ask who
would own watching each one. Unnamed risks still arrive; the only difference is whether
anybody saw them coming.

**4. Open questions.** People suppress these because admitting uncertainty feels like
being unprepared. Say plainly that unanswered questions belong in the file — the ones
left out don't disappear, they resurface in week three as rework. Anything you and the
requester could not settle goes in this section unresolved. That is a feature.

If the answer is discoverable in the repo or the tracker, look it up rather than
spending one of the requester's questions on it.

## Output

Write to `intent/YYYY-MM-DD-<requester-or-client>-<topic>.md` in the project repo —
not under `docs/superpowers/`, which holds what *you* decided rather than what *they*
asked. Create the folder if it doesn't exist.

```markdown
# Intent: <short title, the problem not the solution>
Author: <name> (<role>). Status: draft.
Source: <meeting + date, ticket, thread — where this came from>

## Problem
<What happens today that shouldn't, with a number where one exists.>

## Proposed outcome
<The condition that means it's solved. Still not a solution.>

## Success measure
<The number from Problem restated as a threshold, where it will be read, and the date
it gets checked.>

## Affected users and systems
<Who feels it, and which systems are in the blast radius.>

## Constraints
<Hard limits: data, budget, timeline, systems that can't be touched.>

## Risks
<What might happen that would hurt, and who watches for it. Not technical risk — that
belongs to the design stage.>

## Open questions
<Unresolved. Leave them unresolved.>
```

`Source:` is not in the upstream playbook. Keep it anyway — on client work it is what
turns the file from a note into something you can point at in a disagreement.

`Success measure` and `Risks` come from AI-DLC's Inception outputs. They are the two
fields the maintain stage reads: without a measure with a date on it, nothing ever comes
back to ask whether this worked, and the loop is a waterfall wearing a diagram.

## After writing it

Show the file and ask the requester to correct it — they own it, you only held the pen.
Their edits are the point, not a sign you got it wrong.

`Status: draft` → `accepted` is theirs to flip, and that flip is the gate: no design
work starts before it. Once accepted, commit the file and hand off to `brainstorming`,
which turns an accepted intent into a spec.

## Reviewing an existing intent

Same rule, applied backwards. Look for solutions that leaked into Problem, a Problem
with no number in it, an empty Constraints section (almost always means nobody asked),
a Success measure naming neither a source nor a date, risks that are really constraints,
and Open questions that were quietly resolved into assumptions. See
`references/examples.md` for a worked before/after.
