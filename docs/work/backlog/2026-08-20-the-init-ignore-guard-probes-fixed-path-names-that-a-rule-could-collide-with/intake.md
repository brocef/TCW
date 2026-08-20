## Origin

Found by adversarial review during 2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository (see its refined-outcome.md, "Deferred, with the user's agreement").

## Problem

The guard asks `git check-ignore` about a representative item path built from
fixed names — `<status>/an-item/state.yaml` and `inbox/an-item.md`. A repository
whose ignore rules happen to name those exact paths would have an otherwise
usable store refused.

Narrow, and preferable to the alternatives that were tried (the folder itself
trips on TCW's own `<status>/*` rules; `.gitkeep` is defeated by the negation
those rules carry). Worth revisiting only if a better probe exists.
