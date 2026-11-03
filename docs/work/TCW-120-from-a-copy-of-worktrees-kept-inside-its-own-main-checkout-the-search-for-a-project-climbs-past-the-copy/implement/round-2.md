# Implement round 2 — TCW-120

Answers the code review of round 1 (branch `v4.0.1`, which is `main` with
TCW-119 and TCW-120 merged, HEAD `480fa33e` before this round). Built in the
worktree `.claude/worktrees/v4.0.1` with its own virtual environment
(`.venv/bin/pytest`, `.venv/bin/tcw`). TCW-119's code and folder are not
touched. This round gives no verdict.

## Findings accepted and fixed

### S1 and D1 — a submodule's own linked worktree, and one probe for a checkout

`_checkout_of` treated a submodule's linked worktree as a main checkout of
its own: git reports the submodule's common folder as
`SM/.git/modules/sub`, which is not named `.git`, so round 1 took the
worktree's own top as its main checkout. `worktree_anchors` already read the
main checkout from `core.worktree` in that case. In the reviewer's layout
E1 (superproject `SM`, submodule at `SM/sub` holding project `r`, a separate
repository Y at `SM/sub/p`, the submodule's linked worktree at
`SM/sub/.claude/worktrees/w` and Y's at `w/p`), `tcw -C …/w/p project path
r` said `r` was declared by more than one folder, `w` and `SM/sub`.

Fixed as D1 asked: `_checkout_of(folder)` (`tcw/store/project.py`) is now
the one cached function returning `(top, main, common)`. It runs `git
rev-parse --path-format=absolute --show-toplevel --git-common-dir` once per
folder per process (`_CHECKOUT_CACHE`), and, when the common folder is not
named `.git`, reads `core.worktree` with the same `git config --get` call
`_probe_worktree` made before; `main` is None for a bare repository's
worktree, which records none. Built on it:

- `_probe_worktree` (behind `worktree_anchors`): None for no checkout or a
  bare repository's worktree, `(top, main)` when the two differ, otherwise
  the superproject check as before. Its answers are unchanged.
- `_left_out_of_the_climb`: takes `main` as `top` for a bare repository's
  worktree, as round 1 did, so the walk goes on outward from it.
- `_same_place_in_two_checkouts`: reads `top` and `common` from it instead
  of its own `git rev-parse`.

`_repository_of` keeps its own `git rev-parse --git-common-dir`: unlike
`--show-toplevel`, it also answers inside a git folder and a bare
repository, which its callers rely on.

Test: `test_a_submodules_own_worktree_kept_inside_it_finds_the_root_in_the_copy`
in `tests/test_manifest_worktree.py`, layout E1.

- Red before the fix: `code=1`, "project 'r' is declared by more than one
  folder near this one: …/SM/sub/.claude/worktrees/w and …/SM/sub".
- Green after D1 alone (checked with the S2 change undone).

### S2 — the active worktree's own main checkout was skipped by the walk

The round read as written started its walk at `top.parent`, so the active
worktree's own checkout was never looked at. In the reviewer's layout
(exp2.sh: Y's main checkout `YM`, a monorepo with root `p` and child `q`
naming `p`; a separate repository at `YM/z`; Y's linked worktree at
`YM/z/wt`), with `YM` on 3.x and `wt` on 4.0, `tcw -C YM/z/wt/q project path
p` answered "YM: is a TCW 3.x project … run 'tcw migrate' in it". The call is
now `_climb(named_by, named_by)`.

Test: `test_the_active_worktree_inside_its_own_main_checkout_past_another_repository`.

- Red before the fix: `code=1`, "…/YM: is a TCW 3.x project (tcw-config.yaml
  at its root, no .tcw/ folder); run 'tcw migrate' in it to move it to TCW 4".
- Green after it; red again with only this change undone.

### T1 — a plain checkout pays nothing (spec Goal 4)

`test_a_search_from_a_plain_checkout_starts_no_git_process` uses the
`recorded_processes` fixture (`tests/processes.py`). It calls
`search_rounds` from a plain single checkout and from a folder nested in it
with no anchors, and from a related project's plain checkout while the
active worktree's anchors are given, and asserts each round is the plain
climb and that no process at all was started.

- Mutation: `_under_a_linked_worktree` made to return True. Red: eight
  `git -C … rev-parse --path-format=absolute --show-toplevel …` processes
  recorded, beginning with the nested folder `single/s`. Green with the
  function restored.

### S3 — the guide said the rule held only inside a linked worktree

`docs/guide/multi-repo.md` put the new paragraph before "Which worktree
counts is the one the command runs from: … follows the rules above only
when the command runs inside a linked worktree", which read as covering it.
The code applies the rule wherever the command runs (exp3.sh: from a plain
checkout outside every worktree, a related project kept in a copy does not
reach the copy's main checkout). The paragraph now follows "Which worktree
counts" and opens "One rule holds wherever the command runs, inside a
linked worktree or outside every one", and says it applies when the search
looks from where a folder is, rather than from a main checkout. The
capability's `description.md` and `docs/use-cases.md` S-4 say the same.

### N4 — the entries

The release note's last sentence now reads "`tcw migrate` run in such a copy
no longer writes a manifest entry the original's run does not". Its "no
longer asks you to migrate the original" is kept: with S1 and S2 fixed, no
layout found asks to migrate the original. The exp2 layout with `p` removed
from the worktree answers "not on this machine", not the 3.x message. The
note adds that the fix holds for a submodule. The changelog entry describes
the shared probe and the walk's new start. Both are wrapped to 78 columns as
TCW-119's are.

### N2 — the redundant clause

`_below(folder, main) == Path(".")` in `_left_out_of_the_climb` is deleted:
the main checkout always shares its own common folder, so the
`_repository_of` test already covers it. The suite stays green.

## Not in this change

- **N1** (a bare repository kept as `project/.git` with worktrees beside
  it): recorded in the spec's Notes as known behaviour. Git names the common
  folder `.git`, so `project` counts as the main checkout, and a search from
  a plain clone inside one of those worktrees leaves it out, as 4.0.0
  already does from the worktree itself.
- **N5** (`_git_lines` and `UnicodeDecodeError`): recorded in the spec's
  Notes as a separate change.

## Cost note

The walk now also runs `git config --get core.worktree` once for a checkout
whose common folder is not named `.git` (a submodule, or a bare repository
not named `.git`), cached with the rest. A plain checkout is unaffected (T1).

## Checks

- The full suite, bare `.venv/bin/pytest` from the worktree root:
  `8297 passed, 115 skipped in 1098.11s (0:18:18)`.
- The reviewer's reproductions against the fixed code:
  - exp.sh: E1 submodule worktree `path r` → `…/SM/sub/.claude/worktrees/w`,
    exit 0 (was "declared by more than one folder"); E1 control and E3
    control through `/tmp` → the copy's `w`, exit 0; E2 bare layout from Y's
    worktree → `e2/project`, exit 0; E2b plain clone in the bare layout's
    worktree → not found, exit 1 (N1, unchanged).
  - exp2.sh: 4.0 main → `YM/z/wt`; 3.x main → `YM/z/wt`, exit 0 (was the
    3.x message).
  - exp3.sh: from `far/OUT`, no worktree → "project 'r' is not on this
    machine", as the guide now says.
  - runall.sh: cases 1, 2, 3, 4, 5, 7 → the copy's root, exit 0; case 6 and
    `named g` → not found, exit 1; contrast `mainwt` → `MAIN`; `named r` →
    the copy; mono `list` → `p s`, `path r` → the copy; gap `path ws` → the
    copy; tools `path tools` → `MAIN/tools`, `path r` → the copy.
  - mono.py, gap.py and tools.py rebuilt fresh: mono `project list` → `p
    s`, `path r` → `…/MAIN/.claude/worktrees/w`, `path s` → `…/w/s`; gap
    `path ws` → `BASE/WS/.claude/worktrees/w`; tools `path tools` →
    `…/MAIN/tools`, `path r` → `…/MAIN/tools/wt/w`.
