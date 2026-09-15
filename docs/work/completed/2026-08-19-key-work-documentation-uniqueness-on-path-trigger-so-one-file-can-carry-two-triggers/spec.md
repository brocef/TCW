# Spec — key `work.documentation` uniqueness on (path, trigger)

## Capability changes

**None.** The ledger holds no capability for documentation entries: a
case-insensitive sweep of `docs/capabilities/` matches only
`docs/capabilities/plugin/work-lifecycle/description.md:1`, which is about
reference material at the `request` stage, not about `work.documentation`. There
is nothing to amend, and this change — a validation relaxation inside an
existing config key — does not on its own justify minting the missing records.

**Noted, not actioned.** The item that introduced this config key
(`2026-08-18-serve-documentation-sync-entries-from-tcw-config-yaml-…`) planned
two new capability records in its spec (`spec.md:5-10`) — *Declare which
documents track which changes* and *Read the documentation gate for a change* —
and neither exists in the ledger, though its `refined-outcome.md:65` records
`tcw capabilities drift` as clean. That is a real gap in the ledger and a
possible gap in `drift`; both belong to their own item, not this one. See
`## Notes`.

## Problem

`parse_documentation_entries` keys its duplicate check on `path` alone
(`tcw/store/base.py:1146-1150`):

```python
if path in seen:
    problems.append(f"{where}: duplicate 'path' {path!r}, already "
                    f"declared by entry {seen[path]}")
    continue
seen[path] = index
```

So one file can carry exactly one entry, and a second entry on that file is
dropped from the returned list with a problem raised. Confirmed against the tree
today: two entries on `README.md` under `Public-CLI-API` and `Validation-Rules`
return **one** entry and the problem
`work.documentation entry 1: duplicate 'path' 'README.md', already declared by
entry 0`.

Nothing else in the codebase treats `path` as a key.
`render_documentation` (`tcw/work/resolve.py:228-234`) iterates the list and
prints the trigger beside the path on every line; `_docs`
(`tcw/work/cli.py:929-953`) does the same for the table and emits a flat
`entries` array for `--json`. Both already read correctly with two entries on
one path.

The Markdown fallback has no such constraint — it is prose matched by heading
(`skills/documentation-sync/SKILL.md:27-41`) — so the recommended config form is
strictly less expressive than the fallback it replaces, for any file whose
sections answer to different triggers.

The narrower key is also inconsistent with the file it lives in. Sixteen lines
up, `_parse_bindings` (`tcw/store/base.py:975-989`) already made this exact
decision the other way, and says why:

```python
# Identity is (kind, value, when), not the value alone. The same script under
# two different conditions is the obvious way to say "this prompt for bugs,
# that one for features"; rejecting it would make conditions unusable.
```

The same sentence rewritten for this parser is the whole argument: the same
file under two different triggers is the obvious way to say "this trigger for
the CLI section, that one for the validation section", and rejecting it makes
triggers unusable on any large file.

## Goals

1. Two entries naming one `path` are accepted when their `trigger` differs, and
   both survive into the returned `DocEntry` list.
2. Two entries agreeing on **both** `path` and `trigger` are still one entry
   plus one problem, naming the earlier entry's index.
3. The duplicate message names the trigger, so a reader can see which of two
   near-identical entries collided.
4. Every configuration valid before this change stays valid, with identical
   entries and identical problems.

## Non-goals

- **A `section:` key.** Named in the request as the alternative, not requested
  alongside; the pair carries the case and adds no key.
- **Checking that `path` resolves on disk.** Deliberately excluded by the
  request, and the parser documents the opposite as intentional
  (`tcw/store/base.py:1090-1092`) — this repo's own fourth entry is the
  unresolvable pattern `skills/<component>/SKILL.md`.
- **A repo-wide change to how duplicates are keyed.** See the sweep below: no
  sibling defect was found, so nothing else moves.
- **The migration guide.** `docs/migration-guide-0.21.X-to-1.0.0.md:255-256`
  describes the entry shape but never states the uniqueness rule, so it is not
  made wrong by this change and needs no edit.

## Sweep for sibling defects

Repo-wide, every duplicate-rejection site in the loaders was read for the same
defect — uniqueness keyed on too narrow a tuple:

| Site | Key | Verdict |
| --- | --- | --- |
| `tcw/store/base.py:1146` — documentation entries | `path` | **the defect** |
| `tcw/store/base.py:983` — lifecycle bindings | `(kind, value, when)` | correct; the precedent cited above |
| `tcw/store/fs.py:2191` — capability records | `cap.id` | correct; an id is the identity |
| `tcw/store/project.py:232` — registered nodes | `project.id` | correct; same reason |
| `tcw/store/fs.py:859` — `extends` aliases | project id | correct; an alias must resolve to one target |
| `tcw/store/fs.py:2808` — `plan.md` stage ids | `stage_id` | correct; the id is the address |
| `tcw/store/{fs,project}.py:819,29` — YAML mapping keys | key | correct; a mapping key is unique by definition |

Only the documentation parser keys on a field that is not an identity. The sweep
is repo-wide and finished; nothing was narrowed.

## Design

In `parse_documentation_entries` (`tcw/store/base.py:1079-1154`), change `seen`
from `dict[str, int]` keyed on `path` to a dict keyed on the `(path, trigger)`
pair, and widen the problem text to name both halves. Everything else in the
function — required keys, unknown keys, newline, absolute-path, escape, and
whitespace-in-trigger checks, and the order they run in — is untouched, so an
entry that fails an earlier check still fails it first and never reaches the
duplicate check.

Nothing downstream changes. `DocEntry` is unchanged, so the store adapters
(`tcw/store/fs.py:3137-3149`), the renderer, the `--json` payload, and the
`documentation-sync` skill's per-entry loop
(`skills/documentation-sync/SKILL.md:72`) all keep their contracts; they gain
only the possibility of two rows sharing a path, which each already renders
distinguishably by printing the trigger.

**Litmus test.** Passes trivially. `parse_documentation_entries` is pure node
configuration — it takes an already-loaded object, touches no filesystem, and
never raises. A tracker-backed store parses the same mapping the same way; the
change is to which tuple counts as an identity, which any store can express.

## Acceptance criteria

Each is runnable against the tree by someone who did not write this.

1. `parse_documentation_entries([{path: "README.md", trigger: "Public-CLI-API",
   description: "d1"}, {path: "README.md", trigger: "Validation-Rules",
   description: "d2"}])` returns **2** entries and **0** problems. (Returns
   `1` and `1` today — verified.)
2. The same call with both entries carrying `trigger: "Public-CLI-API"` returns
   **1** entry and exactly **1** problem, and that problem contains
   `entry 1`, `'README.md'`, and `'Public-CLI-API'`.
3. Given `[A(README/X), B(README/Y), C(README/X)]`, the only problem reported
   names entry 2 and says it was already declared by **entry 0**, and the
   returned list is `[A, B]`.
4. Every existing test in `tests/test_documentation_config.py` still passes;
   `test_a_duplicate_path_is_reported` (`:75`) is unchanged, because it
   duplicates a whole entry and so collides on both halves.
5. `pytest` is green across the suite.
6. A `tcw-config.yaml` carrying the reporter's pair — `README.md` under
   `Public-CLI-API` and `README.md` under `Validation-Rules` — passes
   `tcw validate` with exit 0 and no `work.documentation` line in the output.
7. `tcw work docs` in that node prints **two** rows, one per trigger, and
   `tcw work docs --json` returns two objects in `entries`.
8. `tcw work docs` in **this** repo prints the same four rows as before the
   change, byte for byte.
9. `README.md`'s list of what `tcw validate` checks
   (`README.md:763-765`) no longer says a bare "a duplicate path", and states
   the pair rule instead.

## Risks

- **A near-duplicate entry now passes silently.** Copy an entry, reword its
  trigger by a character, and both are accepted — where today the second is
  rejected. Accepted: it is the identical trade `_parse_bindings` already took
  for `(kind, value, when)`, and a trigger is a project-defined name whose
  vocabulary TCW explicitly does not police (`tcw/store/base.py:1086-1089`).
- **Two rows on one path can read as a rendering bug.** In
  `render_documentation` and the `tcw work docs` table the path repeats on
  consecutive lines. Accepted: the trigger is printed on the same line and is
  what distinguishes them; that is the property the request relies on.
- **The change is smaller than the docs edit around it.** The risk is shipping
  the one-line parser change and leaving `README.md` stating the old rule. AC 9
  is there to catch exactly that.

## Notes

- Assumption, not verified against the running project: the reporter will drop
  the `README.md#invalid-constructions` workaround once this lands. Nothing in
  this repo can check that, and nothing here depends on it.
- The ledger gap named under **Capability changes** deserves its own backlog
  item — two records planned, none written, and `tcw capabilities drift` clean
  anyway. Flagged to the user at the end of planning rather than filed silently.
