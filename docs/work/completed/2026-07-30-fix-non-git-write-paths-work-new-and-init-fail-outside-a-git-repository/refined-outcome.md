# Refined outcome — Fail fast with clear errors on non-Git writes

_Accepted._

## The decision

Accepted by the user on 2026-08-20, on a condition they set at `verify`: request
an adversarial Codex review, accept if it passes, and **rework anything it finds
even if not directly related to these changes**. It took six rounds. The sixth
returned `DONE` with its "belongs to this item's subject" bucket empty; the user
approved closing after that round, with the remaining candidates filed rather
than folded in.

`rework.md` was deleted at acceptance, as the refined-outcome template requires
— the verdict must not sit beside its own rejection. Its analysis is folded into
"The first verdict" below, so the artifact spine still carries it.

## Evidence

| Check | Result |
| ----- | ------ |
| `python -m pytest -q` | `1807 passed` |
| Shipped-binary reproduction, all nine defects | every one refuses; manifests byte-identical before/after |
| `tcw capabilities check` · `tcw validate` | `capabilities OK` · `validate OK` |
| Codex round 6 | bucket (a) empty, `DONE` |

Test count moved 1788 → 1807 across the rework: 19 new tests, all watched red
against the unfixed tree with `git stash push -q tcw/store/fs.py` before the fix
was written. Three had to be re-checked because their first red run failed for
the wrong reason (my own fixture bug, not the defect) — recorded below.

## The first verdict, and why it was right

The original implementation shipped a correct guard on the wrong assumption:
**one repository per node.** It guarded `store_git_root` for `FsWorkStore` and
`node_root` for the tree stores, which is right, and the 28-command CLI matrix
proved it — on a default store, where those two are the same directory.

Three flows write to **two** repositories:

| Flow | Guarded against | Also writes |
| ---- | --------------- | ----------- |
| `work start --worktree` | the work store's | the code node's `.gitignore`, the worktree |
| `work complete` on a worktree item | the work store's | the code node's — the merge-back |
| `init --work-path` | *(checked last)* | both |

All three shipped broken. The matrix could not see it because it removed every
repository in the graph at once, so a guard on either repository passed it.
`spec.md`'s mutation walk reasoned "unreachable outside a repository" for
`ensure_worktree_ignored` from the same assumption; that row is corrected in
place (`02357f8`), with the wrong reasoning left legible beside the right one.

The sharpest of the three was not a partial write at all: `complete` **reported
success** while skipping the merge-back, because `merge_worktree` read a failed
`rev-parse` as "branch already gone". A partial write announces itself. A false
completion does not.

## What the six rounds found

| Round | Findings | Nature |
| ----- | -------- | ------ |
| 1 | 5 (3 high) | The three split-ownership writes, a string-valued `cmd`, a test that never built the external store it was named for |
| 2 | 4 (2 high) | All 5 confirmed fixed. New: `init` accepting a gitignored store, a dangling symlink defeating the ancestor walk, `write_sentinel` running before the pristine check, and documentation overstating what `complete` refuses |
| 3 | 3 (2 high) | `git_ignored` missing `--no-index`; `init` learning its leaves only inside the loop that created them; **a regression I introduced in round 2** — hoisting the config read above `write_sentinel` moved its mapping check out from under that read |
| 4 | 2 (1 high) | The ignore check probing only the store root; a falsy `work.path` skipped by a truthiness test. The `plan` refactor verified clean across the full input matrix |
| 5 | 1 (high) | The ignore check asking about `.gitkeep`, which `<status>/*` + `!<status>/.gitkeep` defeats — TCW's own rule shape — and never running for a default store |
| 6 | 0 in scope | `DONE` |

Rounds 3-5 were all about **the ignore guard added in round 2**, which is a
different subject from this item: it catches writes git silently *drops*, not
writes git *refuses*. It is kept because the trap is real and was flagged high
twice, and it carries a `ponytail:` note stating its ceiling — a configure-time
check cannot see a `.gitignore` written after `init`. Bucket (b) below is where
the rest of that subject goes.

## Three tests that first passed for the wrong reason

Worth recording, because the ratio is the point: 19 new tests, three of which
were green on their red run for reasons unrelated to the defect.

- `test_init_refuses_an_external_work_path_before_it_writes_anything` — a
  `commit_all` on an empty repository, which git refuses. Caught by re-running
  it under `git stash push tcw/store/fs.py` and reading the failure text rather
  than the status.
- `test_init_refuses_a_store_whose_status_folder_the_rules_hide` — the check
  fired against the wrong path shape. `git check-ignore` applies a `dir/` rule
  only when it knows the path is a directory, and `init`'s leaves do not exist
  yet.
- `test_init_refuses_a_store_whose_items_the_rules_hide` — round 5's finding in
  test form: the probe answered a question nobody was asking.

The general lesson for this repo's `implement` stage: *watch it red, and read
why.* A red run is not evidence until the failure text names the defect.

## Two checks that exist to catch over-tightening

Both guard fixes could have broken TCW's own scaffolding, so each has a
counterweight test that fails if it does:

- `test_a_plain_start_still_works_when_only_the_node_has_no_repository` — the
  `--worktree` guard must not spread to a plain `start`, which needs only the
  store. An external store is a supported configuration, not a broken one.
- `test_init_still_accepts_the_resolved_status_rules_it_writes_itself` — TCW
  ignores `completed/*` and `discarded/*` on purpose. An ignore check strict
  enough to catch a hidden store is exactly the one that starts refusing TCW's
  own scaffold, and this pins that it does not.

## Deferred, with the user's agreement

Filed as follow-up candidates rather than folded in, all of them bucket (b) —
work needing a mechanism this item does not have:

1. **Write-time ignore enforcement.** The configure-time guard cannot see a
   `.gitignore` written after `init`, a rule naming one slug, or one arriving
   with a later pull. Catching those means a check in `git_stage`.
2. **Probe-name collision.** The guard probes fixed names (`an-item/state.yaml`,
   `an-item.md`); a repository rule naming those exact paths would refuse a
   usable store.
3. **Atomicity against arbitrary git refusals.** An index lock, a hook, or a
   permissions error can still reject staging after the filesystem write. Fixing
   that means rollback, not a precondition.
4. **`load_yaml`'s falsy-document contract.** A `tcw-config.yaml` whose whole
   content is `[]` or `false` reads as an empty mapping rather than a malformed
   one. Every caller shares that contract.
5. **`docs/work/.claiming/` cleanup.** Created by every `start`, never removed.
   Observed in the first `outcome.md` and still true.

## Closeout choices

- **Route:** stays on `main` locally. No merge, no PR, nothing pushed.
- **Version:** no cut. `docs/{changelogs,release-notes}/upcoming.md` keep
  accumulating; they now carry this item plus the stage-prompt work.
- **Documentation:** all four entries evaluated three times over the rework
  (`81c08bc`, `ed1a046`, `5cbeecf`, `5e8148d`, `3cf246c`). `README.md` never
  fired — no command, flag, or exit code changed.
- **Capabilities:** eight entries, in two passes. Planning named three; `verify`
  found `delegate`/`escalate` missing from the sidecar (`92d1736`), and the
  rework added `complete-a-work-item`, `scaffold-the-doc-trees`, and
  `configure-the-work-store-location` (`e559cf5`). No status flips.
- **Post-mortem:** not run. The one thing worth carrying forward is already
  written down twice — a mutation walk scoped to one file, and a matrix built on
  one repository, cannot see a write that crosses to a second one.

## Notes

### For whoever implements next in `tcw/store/fs.py`

`init` no longer computes its leaves inside the loop that creates them: `plan`
holds `(component, base, leaves)` and both the pre-flight and the creation loop
read it. Anything adding a component or a status folder adds it there, once, and
gets the pre-flight for free. Codex verified the refactor preserves created-list
order, `.gitkeep` locations, the returned value, and the ignore-rule branch
across every input combination.

`git_ignored` now takes `no_index`. Default `False` — `git_stage` and `git_mv`
need the tracked-aware answer, because it mirrors what `git add` will do. Only
`init` wants the rules-only one.
