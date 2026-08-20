# Outcome — Resolve taxonomy refs against symlinks, not just lexically

Implemented at `97151e0..HEAD`. Suite green; final numbers under **Test result**.

## What shipped, task by task

The plan's task numbering survived, with two tasks added during implementation
after adversarial review round 2 and one folded in on the user's decision.

| Task | Commit | What landed |
| --- | --- | --- |
| 1 | `776b76d` | `FsTreeStore._within_store` + `_resolved_root` (`cached_property`) |
| 1b | `5d02f69` | Resource containment in `_load_node` / `_compose_body`; `_node_readable`; both `get_local`s |
| 2 | `70bda31` | Taxonomy `add`, `_local_slugs`, `_validation_resources` |
| 3 | `2746e58` | Capabilities `_all_meta_dirs`, `add`, `_write_target`, `_validation_resources` |
| 1b′ / 3b / 4 | `53a910f` | The nine further direct readers, targeted `check`, work `_item_dirs`, and the dangling-symlink collision fix |
| — | `0d6ac4d` | Work-item **resources** (`_present`, `read_artifact`, work `_validation_resources`) |
| 5 | none | No change — see below |
| 6 | not run | See **What was left out** |

Documentation: `d4e875d` (three skills), `406b043` (changelog), `0f6e93a`
(release notes). Spec corrections: `5e86120`. Follow-up filed: `7a7d735`.

## What the plan and spec got wrong

This is the substantial section. Both artifacts were adversarially reviewed
before implementation and revised once; implementation still contradicted them.

**1. `_load_node` is not the shared read chokepoint the plan called it.**
Round 1's fix — the one added *because* the directory guards were found
insufficient — was itself insufficient. Nine further sites read a node's
`meta.yaml` or `description.md` directly, none of them through `_load_node`:
`_local_paths`, `_override_index`, the duplicate-id scan, `check`'s attachment
block, both component `_validation_resources`, `get_term_detail`, `update_term`,
`_apply_override` and `_node_texts`. Each is now guarded. The lesson the plan
should have carried and did not: *"one chokepoint" is a claim to be verified by
grep, not inferred from a call graph.*

**2. An escaped `meta.yaml` reading as `{}` does not make a node absent.**
Task 1b asserted it did, for both node types. It does not: `_term` falls back to
a slug-derived name and a default kind, so an escaped meta produced a **phantom
term** named after its own slug rather than a miss — arguably worse than the
original escape, because it looks like a real entry. Hence `_node_readable`,
which asks the folder question and the own-`meta.yaml` question together. Note a
folder with *no* `meta.yaml` still passes, which is correct: taxonomy allows
meta-less intermediate folders, and `_within_store` on a non-existent path
resolves its prefix and answers `True`.

**3. The plan said "eleven guards"; the real accounting is folder-versus-resource.**
Several of the eleven prove only that a *directory* is inside the store. The
review's demand to replace the count with explicit accounting was right, and the
implementation follows the accounting rather than the count.

**4. Task 5's premise was inverted.** It asked this item to stay clear of an
in-flight sibling's `CalledProcessError` handler. That item is completed and the
handler landed at `tcw/cli.py:190`. The live consequence is the opposite of what
the task described: because *any* git failure now exits 1 with a clean line, a
containment test asserting only "exits 1" passes on the **unfixed** tree, since
that is how these scenarios fail there (git refuses to stage beyond a symlink).
Every containment assertion here is made at the store API for that reason.

**5. Three criteria would have passed on the unfixed tree.** `Path.rglob` does
not descend a symlinked directory, so the spec's criterion 3 descendant half,
criterion 5 listing half, and criterion 7 `list_all` half were all vacuous as
written. The fixtures now point the symlink at a folder that *itself* holds a
`meta.yaml`, which is what makes current `list_all` demonstrably include it.
Every negative assertion has an in-store control beside it.

**6. `_validation_resources` must ask the *owning* store.** Introduced as a bug
by this very change and caught by the existing suite
(`test_transitive_extends_flattens_terms_by_owning_project`): an inherited
entry's files are bounded by *its* root, not the local one, so `self._within_store`
filtered out every legitimate inherited resource. Both components now thread
`owner` through. Worth stating because the same shape appears in
`_apply_override`, where the review correctly insisted **both** sides need
guarding — a resolved upstream root does not stop that store's own
`description.md` from being a symlink.

**7. A dangling or looping symlink at a write target was a traceback.**
Found by the sweep, not predicted anywhere. `Path.exists()` follows symlinks, so
such a link read as absent, the "already exists" refusal was skipped, and
`mkdir` raised `FileExistsError` out of both `tcw taxonomy add` and
`tcw capabilities add`. Pre-existing; reproduced in a scratch repo before and
after. `is_symlink()` joins `exists()`.

**8. The spec's symlink-loop expectation was wrong.** It asked for
`_within_store` to return `False` on a loop. On Python 3.13+ `resolve()` returns
the path *unresolved* and raises nothing, so a loop inside a store answers
`True`; below 3.13 it raises `RuntimeError`, which the planned `except OSError`
would not have caught, crashing `list`. The obligation is *never raises*; the
verdict is don't-care and deliberately not pinned, because pinning it would pin
a Python-version detail. `(OSError, RuntimeError)` is caught.

**9. The spec's work-store non-goal was withdrawn** (`5e86120`), on the user's
decision after review round 2. Its reasoning — no other work-store path joins a
caller-supplied id onto the root — was true and beside the point: the exposure
was a symlinked artifact *inside* a legitimately discovered item.

**10. `_node_texts` belonged on `FsTreeStore` all along.** It was defined on the
capabilities store; taxonomy's `get_term_detail` needed the same read (it used
bare `read_text` with no existence guard, so an absent resource raised
`FileNotFoundError`). Moved up rather than duplicated.

## Test result

`python -m pytest -q` — see the final run recorded at `verify`. The last full
run during implementation: **1880 passed, 0 failed** against a **1859-passed**
baseline measured on `5ddaa31` before any change. `tests/test_store_bounds.py`
is new and carries every containment case.

Each new test was watched **red first**, and the red reason read rather than
assumed — which caught two fixtures failing for the wrong reason: a missing
`tcw-config.yaml` sentinel (the project registry refused the node before any
store code ran) and missing work status folders. Both fixed before the code was
written.

## Abstraction litmus test

Passes, unchanged from the spec's assessment. `_within_store`, `_node_readable`
and `_resolved_root` are private to the filesystem adapter; path containment has
no analog in a remote store, which has no paths to contain. `tcw/store/base.py`
is untouched. The one structural change — `_present` ceasing to be a
`staticmethod` so it can reach the store root — is likewise adapter-private and
has no callers outside `tcw/store/fs.py` (verified by grep).

## What was left out

**Task 6, the measurement pass, was not run.** The plan asked for lookup and
listing microbenchmarks on a synthetic ~2,000-node tree, with a 15%-regression
threshold and a documented fallback (resolve only when the candidate is itself a
symlink). It is not done, and the reason is a judgment call the verifier should
review rather than accept: the change grew from ten directory guards to roughly
twenty guards including per-resource checks, so the plan's per-candidate cost
model no longer describes it, and the numbers it specified would characterise a
design that is not what shipped. The full suite went from 438s to a comparable
figure with no outlier, which is evidence of *no gross* regression and is not
the measurement that was asked for. If the threshold matters, this is the one
task to send back.

## Notes

- **Review rounds.** Two adversarial rounds ran before implementation (round 1
  on the original plan, round 2 on the revision), both returning `NOT DONE` with
  confirmed blockers. Round 2's findings were partly overtaken by
  implementation, which had already found the phantom-term problem
  independently. Every accepted finding was reproduced against the tree before
  acceptance; none was taken on the reviewer's word.
- **Follow-up filed** (`7a7d735`): `docs/work/inbox/2026-08-20-claiming-lookup-embeds-an-unvalidated-slug-into-a-glob.md`
  — `_claiming_dirs` embeds an unvalidated slug into a glob. Real, and a
  different mechanism (identifier validation, not containment).
- **Spec snippet drift.** The spec's Problem §3b reproduction and its cost
  figures were written against `c0b340e`; the code has moved and the guard set
  has grown. The reproductions still reproduce; the line numbers do not resolve.
- **An accidental write into this repo during implementation.** Two `tcw`
  commands intended for a scratch repo ran here, creating `docs/taxonomy/loop-a`
  and `docs/capabilities/ca`. Both were removed before any commit;
  `tcw taxonomy check` and `tcw capabilities check` are clean and nothing
  reached history. Recorded because "nothing reached history" is a claim, and
  the verifier should confirm it: `git log --diff-filter=A -- docs/taxonomy/loop-a
  docs/capabilities/ca` returns nothing.
- **`_parent_slug` edge, accepted rather than closed.** It independently treats
  any ancestor holding a `state.yaml` as an item, so a nested child under a
  folder that `_item_dirs` excluded can still name that excluded folder as its
  parent. Confirmed code path; whether it violates intent is a specification
  question this item does not settle.
