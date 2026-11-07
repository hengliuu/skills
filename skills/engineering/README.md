# Engineering

Skills for changing code and writing the files that steer agents. They keep edits small and checkable, and they help you write context files that earn every line.

| Skill | What it does |
| --- | --- |
| [karpathy-guidelines](karpathy-guidelines/SKILL.md) | Guides how to change code: surface assumptions, write the minimum, keep the diff surgical and name a check that proves it works. |
| [claude-md-author](claude-md-author/SKILL.md) | Writes, audits and slims `CLAUDE.md` and `AGENTS.md` files against a tight instruction budget. |
| [jev](jev/SKILL.md) | Optional. Scores and filters long lists, re-picks each plan task's role and effort, and flags diff hunks worth a second look, through TypeSafe's Jev and your own key. |

The `karpathy-guidelines` skill is also preloaded by the code-writing role agents, and a hook asks for it before the first code write of a session.
