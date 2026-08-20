## Origin

Found by adversarial review during 2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository (see its refined-outcome.md, "Deferred, with the user's agreement"). — and observed once before it, in that item's first `outcome.md`.

## Problem

`FsWorkStore.start` creates `docs/work/.claiming/` and nothing ever removes it,
so a node accumulates an empty directory the first time anyone starts an item.
Harmless in itself, but it invalidates the obvious assertion — `assert not (root
/ "docs/work/.claiming").exists()` — which passes for the wrong reason on any
node that has ever started an item. One test already works around it by using a
node that never started anything, and says so in its docstring.
