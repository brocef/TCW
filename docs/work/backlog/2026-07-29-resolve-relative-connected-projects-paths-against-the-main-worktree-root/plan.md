# Plan — Resolve relative connected-projects paths against the main worktree root

Seven tasks. The spec settled the design; this orders it so the suite is green at
every commit boundary and the riskiest change lands after its infrastructure and
its tests exist.

Ordering rationale: the probe (task 1) is inert on its own and testable in
isolation. Rule 1 (task 2) fixes the reported defect but leaves the graph
reporting a duplicate ID, so **task 2 alone is not a green state for the new
fixtures** — task 3 completes it. They are still separate commits because they
are separately reviewable and separately revertable, and the existing suite stays
green after each; the new worktree fixtures only go green after task 3. That is
stated here so a reviewer bisecting does not read task 2 as broken.

Task 4 (`complete` refusal) is independent of 1-3 and could land anywhere; it is
placed after them so the worktree test environment from task 5 can cover both.

Not a staged-DAG plan: seven tasks over four files is small enough that a
manifest would add indirection without reducing loaded context.

## Task 1 — the git probe

**Changes:** `tcw/store/project.py` — one module-private helper plus a
module-level cache.

Returns `(current_toplevel, main_worktree_root)` when the given directory sits in
a **linked** worktree, `None` otherwise. `None` on every one of: git absent
(`FileNotFoundError`), not a repository, the primary checkout, a bare main repo,
any non-zero exit, any unparseable output. Never raises.

Single invocation:
`git -C <dir> rev-parse --path-format=absolute --show-toplevel --git-common-dir`.
Inside a linked worktree this prints the worktree top then `<main>/.git`; the
main root is that second path's parent. It is a linked worktree exactly when the
main root differs from the toplevel. **Handle the bare main repo**: if
`--git-common-dir`'s parent contains no worktree (a bare repo), return `None`
rather than re-anchoring against a nonsense directory — the spec's Risks call
this out and criterion 6 does not cover it.

Lives in `project.py`, **not** beside `git_root` in `fs.py`: `fs.py` imports
`project.py` (`tcw/store/fs.py:39`), so the reverse import would be circular.

Cache keyed by resolved directory at module level. The spec measured ~8 ms per
probe and six registry opens for `tcw work list -i` on a three-node graph, so an
uncached probe would add ~50 ms to recursive commands. A CLI invocation never
outlives the process, so an unbounded module-level dict is correct here — note
that in a comment so nobody "fixes" it into an LRU.

**Verified by:** unit tests over four cases — inside a linked worktree, in a
primary checkout, in a non-git directory, and with `git` forced to fail
(monkeypatch `subprocess.run` to raise `FileNotFoundError`). All must return the
expected value without raising.

## Task 2 — Rule 1, re-anchor only on escape

**Changes:** `tcw/store/project.py`, `_target_path` (`:256-261`).

`_target_path` is a `@staticmethod` with five call sites (`:180, :182, :266,
:276, :297`); make it an instance method (or have it take the anchor) so the
probe runs once per registry rather than once per locator.

Logic for a **relative** locator, when the probe reports a linked worktree and
the source config lies inside the current worktree:

1. Compute the naive target (`source_config.parent / locator`), resolved.
2. If it is still inside the current worktree top → **keep it**.
3. If it escapes → re-resolve against the source directory's counterpart under
   the main worktree root: `main_root / source_dir.relative_to(current_toplevel)`.

Absolute locators are returned untouched, exactly as today (`:258-260`).

The narrowness is the point: a target that stays inside the worktree is a sibling
node on the same branch and belongs to the worktree. Only a target that leaves
the checkout was authored against the primary checkout's position on disk. This
is what keeps multi-project-in-one-repo working, which the report's literal
remediation broke.

**Verified by:** the reported error is gone from the two-node worktree fixture.
The graph will still report `duplicate project id` at this commit — expected,
resolved by task 3. Existing `python -m pytest -q` stays green.

## Task 3 — Rule 2, collapse the worktree's own identity

**Changes:** `tcw/store/project.py`, same function.

Once the parent is reachable, the current node has two config paths on disk:
`<worktree>/tcw-config.yaml` and `<main>/<rel>/tcw-config.yaml`. The parent's own
locator points at the second, so the registry would register both under one ID
(`:171-176`) and fail reciprocity (`:276-280`).

Map that **one** main-worktree path onto the worktree path, so the graph holds
exactly one node for the current project — the worktree copy (spec Goal 2).

Keep the alias **exactly this narrow**: one pair, only while the probe reports a
linked worktree. A wider alias risks masking a genuine duplicate-ID error, which
is a real validation the registry performs.

**Verified by:** `FsProjectRegistry.open(<worktree>).check()` returns `[]` on the
two-node fixture (criterion 3); `.current.locator` is the worktree (criterion 4);
`_validate_reciprocity` (`:263-306`) passes because both sides now agree; and
`registered_project_id(node, node)` (`tcw/store/fs.py:164-172`) still resolves.

## Task 4 — refuse `tcw work complete` from inside the item's own worktree

**Changes:** `tcw/work/cli.py` `_complete` (around `:837`/`:887`).

Today this exits 0 having done nothing: `merge_worktree(st.node_root, branch)`
(`tcw/store/fs.py:411-429`) merges the work branch into itself, and
`remove_worktree` (`:432-448`) looks for `<worktree>/.worktrees/<slug>`, misses,
and swallows the miss as "already absent" (`:441`). The command claims a
completion that did not happen.

**Refuse rather than support it.** `git worktree remove` on the worktree you are
standing in deletes your own cwd (the spec verified this), so completing from
inside is not a flow worth engineering. Exit non-zero with a message naming the
primary checkout as where to run it.

Detect via the task-1 probe plus the item's own worktree path — do **not**
re-derive paths inline. Refuse only when the item actually has a worktree and the
cwd is inside *that item's* worktree; completing from inside an unrelated
worktree is not this defect.

**Verified by:** criterion 9 — the command exits non-zero and names the primary
checkout; and the negative case, that `complete` from the primary checkout still
merges and tears down exactly as today.

## Task 5 — a fourth test environment

**Changes:** `tests/test_environment_hardness.py`, whose module docstring
(`:1-20`) already describes three environments; add a node inside a linked
worktree as the fourth, and extend the docstring to match.

Covers criteria 1-5, plus the non-git graph (criterion 6) and the absolute-locator
case (criterion 8) if the module's existing shape makes that natural; if not, put
those in `tests/test_project_registry.py` (confirm the actual filename) rather
than forcing them in.

Add the bare-main-repo probe case from task 1's Risks here or beside task 1's
unit tests — it needs a `git init --bare` fixture and must assert the probe
returns `None`.

**Verified by:** the new environment passes; no existing test is modified
(criterion 7 — if an existing test needs editing to accommodate the change, that
is a regression signal, not a test to update).

## Task 6 — capabilities and taxonomy wording

Runs the capabilities gate. **REQUIRED SUB-SKILL: use `tcw-capabilities`.**

1. **New** `cli/run-from-a-git-worktree` — "Run TCW from inside a git worktree."
   Seed `Status: Missing` with `Planning doc` pointing at this item, then flip to
   `Supported` before completion. `Feature: connected-project-registry`,
   `Subject: node`. Declare it in this item's `capabilities.yaml` sidecar under
   `new:` — the completion gate enforces that a declared `new:` capability no
   longer reads `Missing`.
2. **Changed** `cli/host-multiple-projects-in-one-repo` — its `description.md`
   closes with "TCW derives deeper ancestry from the registered graph **without
   scanning directories or git metadata**." That becomes false in the letter.
   Bound it to what it was actually asserting: the *graph* is not inferred from
   layout. Declare under `changed:`.
3. **Changed** `work/complete-a-work-item` — gains the task-4 refusal.
4. **Taxonomy axis** — `docs/taxonomy/node/description.md` says node relations
   come "only from reciprocal registered locators, independent of filesystem
   nesting or git layout". Same bounding problem. Edit it; it is a taxonomy edit,
   not a capability one, so it does not belong in the sidecar.

## Task 7 — documentation sync

One pass over the finished diff, per `stage-implement.md` step 6. Predicted:

| Entry | Trigger | Expected |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fires** — `Fixed`: relative connected-project locators re-anchored to the main worktree root on escape; worktree identity collapsed; `complete` refuses from inside the item's worktree. Record that the reported remediation was insufficient and why. |
| `docs/release-notes/upcoming.md` | `Public-API` | **fires** — TCW now works from inside a git worktree; and `complete` from inside a worktree now refuses instead of silently doing nothing. |
| `README.md` | `Public-API` | **check** — README documents `--worktree` and the connected-projects config. If it states or implies that relative locators resolve against the config's own directory, that is now conditionally false. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **check** — `skills/tcw-work/references/transitions.md` documents `complete`'s worktree merge-back and gates; the new refusal is a gate and likely belongs there. Also check `references/commands.md`. |

## Verification

Fixtures are throwaway git repos created under
`/private/tmp/claude-501/-Users-brian-Projects-TCW/aed28ea1-65fe-4658-9f64-7aa452b6b335/scratchpad`.
**Never create a git worktree inside `/Users/brian/Projects/TCW`** — this repo is
the editable install under test, and a stray worktree would pollute it.

Beyond the suite, run by hand and paste actual output into `outcome.md`:

1. The spec's Problem-section reproduction, re-run after the fix: all five
   commands exit 0 from inside the worktree, `tcw validate` prints `validate OK`.
2. The multi-project-in-one-repo fixture from criterion 5, confirming the parent
   locator is the **worktree's** repo top — this is the case the report's
   remediation regressed, so it is the one most worth seeing with real output.
3. The non-git graph (criterion 6), confirming byte-identical behavior to HEAD.
   Capture HEAD's output **before** implementing, or the comparison is a claim
   rather than a measurement.
4. The `complete`-from-inside-worktree refusal (criterion 9), plus the positive
   control that `complete` from the primary checkout still merges and tears down.

Note the editable install points at the primary checkout, so throwaway fixtures
exercise the patched code directly.

Full `python -m pytest -q` green before `submit`.

## Notes

**`state.yaml` records effort `low`; this is `medium`.** Two resolution rules, a
CLI refusal, a new test environment, a new capability and three wording edits.
Update the field during implementation rather than leaving the estimate lying.

**Follow-up item to create, not fix here:** non-git **write** paths are broken
independently. Reads work without git (`work list`, `validate`, `work nodes` all
exit 0 in a repo-less tree) but `tcw work new` dies with an unhandled
`CalledProcessError` from `git_stage` (`tcw/store/fs.py:640` → `:262`) and
`tcw init` refuses outright (`tcw/cli.py:30`). Found by this item's sweep, out of
its scope, and it must not be lost — file it via `tcw work new` before this item
completes.

**GitHub issue #9 is not closed at completion** — deferred until the containing
minor version is cut and pushed, per the user's 2026-07-30 decision.
