# Outcome — Retain resolved work items in history, and make auto-delete configurable

## What shipped

Nine planned tasks in two commits (code, then documentation).

1. **`parse_retention`** in `tcw/store/base.py`, beside the other pure config
   parsers, defaulting every `RESOLVED_STATUSES` member to `True` and returning
   the safe value *and* the problem for a malformed setting.
2. **`FsWorkStore.retention_conflicts`** and its report in `tcw/validate.py` —
   an *explicit* `retain: true` against a gitignored folder. See Corrections for
   why explicit.
3. **`_require_deletable`**, the interlock, refused before the move.
4. **`Tombstone.location`**, written by `_write_tombstone` and read back by
   `tombstone()`. The dataclass docstring, which forbade a locator outright, now
   states the narrowed rule and why the premise changed.
5. **`FsWorkStore.delete_resolved`** — the second commit, re-runnable, tolerant
   of an already-absent folder.
6. **Publication** carries both commits; `_publish_after_transition` runs after
   the deletion. Read-and-assert plus a new test.
7. **`tcw work show`** answers from the graveyard, resolving the recorded commit
   through `describe_location` before showing it.
8. **`tcw work init`** writes no ignore rules for a status named in `retain`;
   `resolved_ignore_rules` takes a `statuses` subset.
9. **Documentation:** README (the three arrangements, the interlock, the
   migration order, the honest cost), release notes, changelog, the `tcw-work`
   transitions and commands references, and three capability bodies.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
4 failed, 2290 passed in 345.68s (0:05:45)
```

The four environmental failures established in item 1.

New: `tests/test_retention.py` — 18 tests covering the parser, the inert
default, the interlock, the two commits, retrievability, slug reuse,
re-runnability, and `show`. Plus one in `tests/test_store_publication.py`
asserting both commits reach the remote from a provisioned store.

The load-bearing one:

```python
def test_the_recorded_commit_still_holds_the_documents(tmp_path):
    root = _node(tmp_path, retain={"completed": False})
    slug = _resolve(root)
    grave = FsWorkStore.open(root).tombstone(slug)
    shown = subprocess.run(
        ["git", "-C", str(root), "show",
         f"{grave.location}:docs/work/completed/{slug}/state.yaml"], ...).stdout
    assert "title: A thing" in shown and "resolution: done" in shown
```

## Corrections

- **The SHA is written in the second commit, not by amending the first.** The
  plan flagged the circularity and proposed an amend. Amending changes the very
  hash being recorded, so it is circular too. Commit 1 holds the item; commit 2
  removes it *and* writes commit 1's SHA. No amend, no self-reference.
- **`Tombstone` forbade exactly this field**, in a docstring the spec did not
  read: *"There is deliberately no locator… A pointer that silently stops
  working is worse than no pointer."* That reasoning was written when a resolved
  item was never committed, so every pointer was to something no clone had.
  Retention changes the premise, and the half of the rule that still holds —
  nothing may fail *silently* — is now enforced by `describe_location`, which
  resolves the handle and reports an unresolvable one. The docstring has been
  rewritten to say all of this rather than left contradicting the code.
- **The conflict report fires only on an explicit `retain: true`.** Reporting the
  default would have fired on every existing node, including this repository —
  a real contradiction turned into noise, and a breach of criterion 1.
- **`git_ignored` had to be asked about a path inside the folder.** The rule is
  `<prefix>/<status>/*`, which matches contents rather than the directory, so
  `check-ignore` on the folder answers "not ignored" however the rules read. The
  interlock silently did nothing until a test caught it. A never-existing probe
  filename is what it asks about now.
- **`WorkStore.transition` had to stop re-reading the item it just moved.** Under
  `retain: false` the item is gone by the time the move returns, and
  `_require(slug)` raised `no such work item` for a transition that had
  succeeded. It now returns the moved item.
- **Criterion 9's resume is a store operation, not a CLI verb.**
  `delete_resolved` is directly re-runnable and tested as such; the
  `tcw work delete <slug>` verb belongs to the blocked follow-up item, as
  planned.

## Notes

Nothing in this repository is configured to auto-delete, and nothing in it
changes: `tcw validate` is clean, the ignore rules are untouched, and the
resolution path for a node declaring nothing is byte-identical.
