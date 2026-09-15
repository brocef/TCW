# Refined outcome — Resolve relative connected-projects paths against the main worktree root

**Verdict: accepted**, by the user on 2026-07-30, after a defect found in
verification was fixed rather than deferred.

The `verify` assessment was delegated to the read-only `tcw-verifier` agent, which
rebuilt every fixture from scratch and re-materialized the pre-change source with
`git archive d795ac9` to measure HEAD-state behavior independently, rather than
reading claims off `outcome.md`. The coordinating session re-ran the suite and
both checks itself.

## Defect found in verification, and fixed before acceptance

**`worktree_anchors` split git's output on whitespace instead of on lines**
(`tcw/store/project.py`). `git rev-parse` emits one path per line; `.split()`
yields four tokens for a repo path containing a space, trips the `len(out) != 2`
guard, and returns `None` — silently reverting every command inside that worktree
to the pre-fix failure. Criteria 1-5 did not hold for that class of user.

Reproduced in the coordinating session before acting, on a `my repo` fixture:

```
raw: '…/my repo/.worktrees/wt\n…/my repo/.git\n'
.split()      -> 4 tokens
.splitlines() -> 2 lines
```

Not a rare case on macOS: `~/My Drive`, `~/Google Drive`,
`~/Library/Mobile Documents`, or any project folder with a space. **No test could
have caught it** — pytest's `tmp_path` never contains spaces, which is exactly why
the regression test added with the fix uses a `tmp_path / "my repo"` subdirectory.
Confirmed red against `.split()` before being committed green.

Fixed in `283bc0d`, with the reasoning left as a comment at the call site so the
next reader does not "simplify" it back.

The failure direction was safe — a space-containing path can never yield exactly
two tokens, so it could not produce a *wrong* anchor — but the feature was dead,
which is why this was folded in rather than filed.

## Evidence, criterion by criterion

All verified against running code on independently built fixtures.

| # | Verdict | Evidence |
| --- | --- | --- |
| 1 | met | Spec's two-node fixture; `work list`, `work nodes`, `capabilities list`, `taxonomy list`, `validate` all exit 0 from the worktree; `validate OK` |
| 2 | met | `tcw work nodes` prints `parent: example-app` |
| 3 | met | `FsProjectRegistry.open(<worktree>).check()` → `[]` — no duplicate ID, no reciprocity failure |
| 4 | met | `current.locator` is the worktree; `tcw work new` from the worktree landed in the worktree's `docs/work/backlog/` while the primary's stayed empty |
| 5 | met | `mono-root` + `sub-a`/`sub-b` fixture: `check() == []`, `parent: mono-root`, and `parent.locator` is the **worktree's** repo top — the case the reported remediation regressed |
| 6 | met | Non-git two-node graph run under pre-change source and under HEAD, `diff -u` → no differences. Measured, not assumed |
| 7 | met | Only four deletions under `tests/`, all comment/docstring/import-reformat. No assertion, body, or fixture touched |
| 8 | met | All-absolute graph: `check()` → `[]` from both the worktree and the primary checkout — same graph in both places |
| 9 | met | From the item's own worktree: exit 1, names the primary checkout, worktree intact. Positive control from the primary: branch merged, worktree gone, exit 0 |
| 10 | met | `tests/test_environment_hardness.py` gains the fourth environment with 10 tests, spanning criteria 1-6, 8 and 9 — broader than the criterion asked |
| 11 | met | `capabilities OK`, `validate OK` |

**Suite:** `python -m pytest -q` → `1150 passed in 170.59s`, re-run in the
coordinating session after the `.splitlines()` fix.

## The spec correction, independently confirmed

The implementer found that absolute locators **are** affected by the bug,
contradicting the spec's original Problem point 1. The verifier reproduced the
HEAD-state failure on an all-absolute graph and got exactly the claimed pair
(`duplicate project id`, `does not point back`), and confirmed in the source that
Rule 1 stayed relative-only while Rule 2 applies to both.

**Criterion 8's rewrite was judged honest, and harder.** The original asserted a
property of one function ("absolute locators are untouched"); the replacement
asserts a property of the system ("resolves the same graph inside and outside a
worktree"). An implementation satisfying the old wording literally would *fail*
the new one — so this is a criterion corrected toward the requirement actually
wanted, not relaxed to fit what was built. That was the specific failure mode the
verifier was asked to watch for, and it is the opposite of what happened.

## Checks beyond the criteria

- **Abstraction litmus test: passes cleanly.** `tcw/store/base.py` has an **empty
  diff**. No abstract interface method was added, so a remote adapter has nothing
  new to implement. `worktree_anchors` has two call sites; the second (the
  `complete` path) sits behind `if has_worktree` beside already-FS-only
  `merge_worktree`/`remove_worktree` — an FS-only guard on an inherently FS-only
  flow, since a Jira-backed store has no `item.worktree` at all.
- **The `complete` refusal cannot false-positive.** `own` is built from *this
  item's* `item.worktree`; equality with the current worktree top can only hold
  when you are standing in that item's worktree. Confirmed empirically from an
  unrelated worktree — not refused, exit 0.
- **The bare-repo heuristic fails safe.** `common.name != ".git"` → decline →
  behave as HEAD does. Its documented hole requires a bare repo literally named
  `.git`, and even then the registry reports `registered target has no
  tcw-config.yaml` — loud, not silent. The opposite discriminator would have been
  the dangerous one. A submodule's common dir also declines correctly.
- **Harness compatibility: unaffected.** The guarantee lives in the CLI. No
  Claude-only mechanism in the `skills/`/`commands/` diff.
- **Repo hygiene:** `git worktree list` shows only the primary checkout.

## Corrections made during verification

1. `.split()` → `.splitlines()` plus a space-in-path regression test (`283bc0d`).
2. `docs/capabilities/cli/run-from-a-git-worktree/description.md` said "Absolute
   locators are followed as written" — true of Rule 1, loose given Rule 2 aliases
   an absolute locator naming the current node's counterpart. Tightened (`2ea3a32`).
3. `outcome.md` said three test-tree deletions; there are four (a reformatted
   import). Substance of criterion 7 unaffected; the count is corrected in place
   with a note explaining the miscount (`2ea3a32`).

## Deferred follow-ups

- **Filed:** `2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository`
  — reads work without git, writes do not. Found by this item's sweep, out of its
  scope, and its request carries the measurements plus the contract question (is
  git a precondition or an enhancement?) rather than presupposing a fix.
- **Recorded, not filed:** `tcw work complete` from inside an *unrelated* worktree
  is still permitted and merges against that worktree. Not the reported defect and
  no fixture exercises it, but the same class of confusion — someone should decide
  whether it deserves the same refusal.

## Closeout choices

- **Route:** committed directly on `main`; no worktree, no PR. Ten commits:
  `8edc17f`, `120a590`, `9fa72c4`, `08910e2`, `efd923a`, `0bffbc1`, `afffe3b`,
  `39b73df`, `1029093`, plus verification fixes `283bc0d` and `2ea3a32`.
- **Version:** none cut at closeout; folded into the single **minor** bump
  covering this batch, per the user's decision on 2026-07-30.
- **Definition of Done:** `tests pass`, `docs synced`, `capabilities reconciled`,
  `reviewed`, `version offered` all satisfied.

  The sixth entry — *originating GitHub issue answered and closed* — **applies and
  is deliberately deferred, not missed.** This item resolves
  [GitHub #9](https://github.com/brocef/TCW/issues/9). Per the user's 2026-07-30
  decision, an issue is answered only after the containing version is cut **and
  pushed**, so it is never closed while the fix is uninstallable.

## Notes

Worth carrying into the #9 reply: the reporter's diagnosis of the *cause* was
exactly right and the reproduction faithful, but the proposed remediation was
insufficient in two independent ways — it leaves a duplicate-ID and reciprocity
failure behind, and it regresses multi-project-in-one-repo. Saying so is more
useful than "fixed", and it credits the diagnosis while correcting the fix.

The `.splitlines()` defect is the argument for having run a verification pass at
all. Every acceptance criterion passed before it was found, because every fixture
lived under a space-free `tmp_path`.
