# Spec — `tcw work new` prints the content.md path

## Problem
`tcw work new` prints only the slug (stdout) and a next-step hint (stderr). To
edit the new item you must separately run `tcw work path <slug>` and append
`content.md`. Agents and humans want to jump straight into the body file.

## Behavior
After creating the item, `tcw work new` prints the absolute path to the item's
`content.md` to **stderr** (so stdout stays slug-only and scriptable), formatted
as a hint line alongside the existing next-step guidance:

```
<slug>                                              # stdout (unchanged)
→ edit: <abs>/content.md                            # stderr (new)
→ next: when you begin implementing, run ...         # stderr (unchanged, epics excepted)
```

Applies to every `work new` (root, `--parent`, `--epic`). Epics keep their own
next-step omission; the edit line is shown for them too.

## Out of scope
- No change to `tcw work path` (stays directory-only).
- No abstract `WorkStore` method — the body filename is an FS realization.

## Capability
Extends **work#open-a-work-item** (already Supported); wording updated at
completion, status unchanged.
