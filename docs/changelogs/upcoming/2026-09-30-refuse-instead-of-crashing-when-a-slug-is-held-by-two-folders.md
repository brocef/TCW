## Fixed

- A slug held by two item folders no longer crashes `tcw work list`, `start`,
  `submit` or `rework` with a `MultipleMatch` traceback.
  - `main` (`tcw/cli.py`) catches `MultipleMatch` as it does `ValueError`.
  - `_find`'s message names every folder and points at `tcw validate`.
  - The board marks the duplicated slug's row (`!` for stages,
    `held by N folders — see tcw validate`); `unresolved_blockers` counts a
    blocker held twice as still blocking; `epic_completable` reads a duplicated
    epic as not ready; the descendant board treats a duplicated initiative
    holder as none.
  - The blocker-cycle refusal's remedy for a slug held twice points at
    `tcw validate`.
- `tcw validate` itself was fixed for this case by #58.
