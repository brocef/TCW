# `tcw validate` crashes on a slug two folders hold

Found reviewing `2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`.

Copy an item's folder from `docs/work/backlog/` into `docs/work/active/` and run
`tcw validate` in that project: it exits 1 with an uncaught `MultipleMatch`
traceback, raised from `FsWorkStore.check` → `_parent_problems` → `_find`
(`tcw/store/fs.py`, around line 7062).

`validate` is where TCW sends people to find what is broken, so it should
report the duplicate — naming both folders — rather than crash. The blocker
refusal for a duplicate slug deliberately does not point at `validate` until it
can.
