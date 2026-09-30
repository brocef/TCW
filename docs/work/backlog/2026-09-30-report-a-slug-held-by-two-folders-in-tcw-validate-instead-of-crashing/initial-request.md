# Report a slug held by two folders in tcw validate instead of crashing

## What is wanted

`tcw validate` should report a slug that two item folders hold, naming both
folders, instead of crashing.

Reproduction from the entry: copy an item's folder from `docs/work/backlog/`
into `docs/work/active/` and run `tcw validate`. It exits 1 with an uncaught
`MultipleMatch` traceback, raised from `FsWorkStore.check` →
`_parent_problems` → `_find` (`tcw/store/fs.py`, around line 7062).

`validate` is where TCW sends people to find out what is broken, so it must not
be the thing that breaks. Once it reports duplicates, the refusal a blocker
gives for a duplicate slug can point people at `validate`, which it
deliberately does not do today.

## Notes

- Found reviewing
  `2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`.
- Interaction: `2026-09-30-keep-an-item-s-folder-in-one-place-and-its-status-only-in-state-yaml`
  removes status folders. Two folders for one slug is still possible after it
  (a copied folder under another name, say), but the reproduction above would
  change. Whichever item lands second should recheck the other.
- Reference material: asked; none provided beyond the entry.
- Written at triage from the entry; the maintainer raised no questions on it.
