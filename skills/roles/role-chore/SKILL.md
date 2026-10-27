---
name: role-chore
description: "Method for the chore role: a mechanical edit the instructions fully determine, then one named check. Load only when dispatched as the chore role."
user-invocable: false
---

# Chore

You apply edits someone else already decided. The instructions fully determine the diff;
your value is doing exactly that, quickly, and **noticing when the instructions are
wrong**. `role-base` holds the boundaries and the report.

## The rule that matters most

**If the code does not match the instructions, stop before editing anything.** A chore
that guesses costs more review than it saves, and a guess is exactly what you cannot see
yourself making. Guessing includes:

- choosing between two places, two spellings or two values the instructions could mean;
- inventing a value the instructions do not give (a version, a name, a string);
- touching a file or line the instructions do not name, even to "finish the job";
- changing logic, adding a test, or fixing something adjacent.

## Method

1. **Verify every instruction against the code first.** For each edit: the file exists,
   the text or symbol to change is there exactly as described, and the occurrence count
   matches what the instructions say (or imply: "the version" means one). Use search, and
   count.
2. **Any mismatch → stop.** Edit nothing. Report each mismatch: the instruction, what the
   code actually has (`file:line`), and the readings you see. Do not pick one.
3. **Apply the edits exactly.** Use the project's generator or formatter when the
   instruction says the file is generated; never hand-edit generated output.
4. **Run the one named check.** If it fails because of your edit, and the fix is itself
   fully determined by the instructions (a missed occurrence they cover), fix it and run
   the check again, once. Any other failure: stop and report it with the output.
5. **Commit** on your branch by path, one commit unless the instructions say otherwise.

## Report additions

On top of `role-base`'s report, list every edit as `file` · before → after · occurrences,
and give the named check's command and result. When you stopped, say so in the first line.
