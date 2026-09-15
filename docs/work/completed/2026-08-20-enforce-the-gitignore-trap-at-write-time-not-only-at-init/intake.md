## Origin

Found by adversarial review during 2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository (see its refined-outcome.md, "Deferred, with the user's agreement").

## Problem

`init` refuses a work store whose items the repository's ignore rules would
hide. That guard is configure-time only, and its `ponytail:` note in
`tcw/store/fs.py` says so: it cannot see a `.gitignore` written after `init`, a
rule naming one slug, or a rule arriving with a later `git pull`. In any of
those cases `git_stage` silently drops the path from the `git add` it builds,
and the item is real on disk and absent from version control.

## Shape

The check belongs where the write happens — `git_stage` already computes which
paths it is dropping. The open question is what it should do about it: refusing
would break `completed/`/`discarded/`, which are ignored on purpose, so it needs
to distinguish deliberate from accidental. Warning may be the honest answer.
