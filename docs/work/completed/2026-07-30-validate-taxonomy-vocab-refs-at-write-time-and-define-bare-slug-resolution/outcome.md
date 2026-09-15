# Outcome — Validate taxonomy `--vocab` refs at write time and define bare-slug resolution

All six plan tasks shipped, in order, one commit each. The follow-up item the
plan's Notes called for is filed. `get()` was not touched.

## What shipped

| Task | Commit | Subject |
| --- | --- | --- |
| 1 — bound refs to the store root | `ad77395` | `fix(taxonomy): bound refs to the store root` |
| 2 — extract the ref-problem helper | `75eebdf` | `refactor(taxonomy): one ref-problem helper for check and update_term` |
| 3 — leaf-slug fallback | `83b1612` | `feat(taxonomy): resolve a unique leaf slug at the vocabulary write boundary` |
| 4 — `add` fails closed | `fd954ba` | `fix(taxonomy): add fails closed on --vocab refs` |
| 5 — capabilities axis | `f9fcdcd` | `caps(taxonomy): state what a --vocab ref may be, and that rm is bounded` |
| — follow-up item | `b796fb6` | `tcw work: file capability ref validation as a follow-up item` |
| 6 — documentation sync | `e1e116f` | `docs: --vocab ref forms, the write-time refusal, and the bounded path` |

**Task 1.** `get_local` routes its ref through `_safe_store_id` before joining it
onto `self.root`; a rejected ref returns `None` rather than raising, so `check`
reports it dangling instead of crashing, `show`/`rm` say "no such term", and no
caller learns a new exception. Two regression tests: the `rm` deletion escape
(the worst failure mode — it deleted real folders) and a `..` ref already stored
in a `meta.yaml`.

**Task 2.** `_ref_problem` (classification) + `_require_ref` (its raising form)
+ module-level `_wrong_kind_ref` (the one shared sentence). Landed as pure
motion: **no test modified**, every message byte-identical. See the correction
below on why the helper returns codes rather than messages.

**Task 3.** `_resolve_vocab_ref` retries a dangling ref as a leaf slug against
`_local_slugs()` — one match resolves to its full path, several raise an
ambiguity naming every candidate, none keeps "does not resolve". Local terms
only. `get()` untouched.

**Task 4.** `add` validates before the first `mkdir` (the `_write_node` call is
the only thing in `add` that creates directories, and the ref resolution happens
while building `meta`, strictly before it), enforces the Feature-requires-a-ref
rule, and stores the resolved path. The fix is in the store, so
`POST /api/taxonomy` inherits it.

**Task 5.** Both capability bodies updated; both stay `Supported`.
`tcw capabilities check` → `capabilities OK`. The item's missing
`capabilities.yaml` was created (see corrections).

**Task 6.** One `documentation-sync` pass over the finished diff. Fired:
`README.md` [Public-API], `docs/release-notes/upcoming.md` [Public-API],
`docs/changelogs/upcoming.md` [Any-Code-Change], `skills/tcw-taxonomy/SKILL.md`
+ `references/init.md` [Skill-Driven-Component] — exactly the five the plan
predicted. No version cut.

## Test result

```
$ python -m pytest -q
........................................................................ [ 99%]
.......                                                                  [100%]
1159 passed in 180.21s (0:03:00)
```

Baseline before task 1 was 1150 passed; the nine added are the two traversal
regressions and seven `add`-behavior tests (including the new serve
422-and-no-folder case).

## Manual verification

Everything below ran in throwaway repos under the session scratchpad. Nothing
involving a `..` ref was ever run inside this checkout.

### 1. The spec's Problem-section reproduction, re-run

All five `add` cases that exited 0 at HEAD now behave per criteria 1–5.

```
tcw tcw 0.17.3
Added term alpha
Added term alpha/zeta
--- (1) nonexistent ref ---
tcw taxonomy add: vocabulary ref 'this-does-not-exist' does not resolve
exit=1
alpha good-feature good-vocab <- no f/
--- (2) bare leaf slug ---
Added term f
exit=0
name: F
kind: Feature
relatesTo: []
vocabulary:
- alpha/zeta
taxonomy OK
check exit=0
--- (3) ambiguous leaf slug ---
tcw taxonomy add: vocabulary ref 'zeta' is ambiguous: alpha/zeta, beta/zeta
exit=1
alpha beta f good-feature good-vocab <- no g/
--- (4) empty --kind feature ---
tcw taxonomy add: Feature requires at least one vocabulary ref
exit=1
alpha beta f good-feature good-vocab <- no h/
--- (5) vocab ref pointing at a Feature ---
tcw taxonomy add: vocabulary ref 'good-feature' points to Feature, expected Vocabulary
exit=1
alpha beta f good-feature good-vocab <- no i/
--- (6) full path stored verbatim ---
Added term j
exit=0
vocabulary:
- alpha/zeta
--- final check ---
taxonomy OK
exit=0
```

Case (2) is criterion 2 end to end: `--vocab zeta` stored `alpha/zeta`, and the
`check` immediately after exits 0 — `add` and `check` cannot disagree.

### 2. The traversal reproduction, with `ls` before and after

```
--- before ---
do-it
--- show ../capabilities/thing/do-it ---
tcw taxonomy show: no such term: ../capabilities/thing/do-it
exit=1
--- add --vocab ../capabilities/thing/do-it ---
tcw taxonomy add: vocabulary ref '../capabilities/thing/do-it' does not resolve
exit=1
--- rm ../capabilities/thing/do-it ---
tcw taxonomy rm: no such term: ../capabilities/thing/do-it
exit=1
--- after ---
thing
do-it
--- a '..' ref already stored in a meta.yaml ---
legacy: dangling vocabulary ref '../../capabilities/thing/do-it'
1 problem(s).
exit=1
do-it
```

`ls docs/capabilities/` after the `rm` prints `thing`, and
`ls docs/capabilities/thing/` prints `do-it` — the folder that used to be
deleted is intact. At HEAD the same sequence left `docs/capabilities/`
containing only `.gitkeep`. The stored-`..`-ref case is reported dangling, with
no traceback and no deletion.

### 3. Criterion 8 against a running `tcw serve`

```
--- POST with an unresolvable vocabulary ref ---
{"error": "vocabulary ref 'no-such-term' does not resolve"}
HTTP 422
alpha <- no broken-feature/

--- POST with a leaf slug that resolves ---
{"term": {"slug": "ok-feature", ..., "vocabulary": ["alpha/zeta"], ...},
 "coreRevision": "ccd168ebbf068687"}
HTTP 201

name: Ok feature
kind: Feature
relatesTo: []
vocabulary:
- alpha/zeta
```

422 (not 201, not 500), no folder created. The web path also inherits leaf-slug
resolution: `"vocabulary": ["zeta"]` was stored as `alpha/zeta`.

### 4. Criterion 12 — this repo's own taxonomy

```
$ tcw taxonomy check
taxonomy OK
exit=0
```

`tcw validate` on the whole node: `validate OK`. As the spec notes, this is weak
evidence on its own (every stored ref here points at a root-level term); the
throwaway-repo checks above carry the weight.

### Working tree

`git status --short` is clean, and
`git diff --diff-filter=D --name-only ad77395~1..HEAD -- docs/` is empty — these
seven commits delete nothing under `docs/`. (The wider `5d688a0..HEAD` range does
show `docs/work/review/…worktree-paths…/` deletions; those belong to another
session's `tcw work complete`, commit `8c14f63`, not to this item.)

## Acceptance criteria

| # | Status | Evidence |
| --- | --- | --- |
| 1 | met | Verification 1 case (1): exit 1, message names `this-does-not-exist`, no `f/`. Test `test_add_refuses_unresolvable_vocab_ref`. |
| 2 | met | Verification 1 case (2): `vocabulary: [alpha/zeta]`, `check` exits 0. Test `test_add_resolves_a_unique_leaf_slug_to_its_path`. |
| 3 | met | Verification 1 case (3): `is ambiguous: alpha/zeta, beta/zeta`, no `g/`. Test `test_add_ambiguous_leaf_slug_names_both_candidates`. |
| 4 | met | Verification 1 case (4): the same "Feature requires at least one vocabulary ref" string `check` uses, no `h/`. |
| 5 | met | Verification 1 case (5): "points to Feature, expected Vocabulary", no `i/`. |
| 6 | met | Verification 1 case (6) for the full path; `test_add_stores_a_resolving_ref_verbatim` covers all three forms — `alpha/zeta`, a bare `Argument` resolving through an `extends` alias, and `shared/Argument` — each stored exactly as given. |
| 7 | met | Verification 2, all three halves, with `ls` before/after showing `docs/capabilities/thing/do-it` intact. |
| 8 | met | Verification 3: HTTP 422, no folder. Test `test_unresolvable_vocab_ref_is_refused_not_warned`. |
| 9 | met in substance — see note | The three-way validation exists once (`_ref_problem`), and `check`, `update_term` and `add` all reach it. The literal grep returns **two** lines, neither a duplicate of the other; details below. |
| 10 | met | 1159 passed. `tests/test_taxonomy.py` federation tests (`test_resolution_unique_extended`, `test_resolution_local_wins_bare`, `test_resolution_ambiguous_errors`, `test_get_term_detail_of_inherited_term`) are unmodified — the diff of that file is additions only. |
| 11 | met | `e1e116f` (SKILL.md, references/init.md, README.md, both `upcoming.md`) and `f9fcdcd` (`docs/capabilities/taxonomy/add-a-term/description.md`). |
| 12 | met | Verification 4. |

**Criterion 9, precisely.** `grep -n "points to" tcw/store/fs.py`:

```
731:    return f"vocabulary ref '{ref}' points to {kind}, expected Vocabulary"
1701:            return [f"{where}: Feature → ref '{feature}' points to "
```

Line 731 is `_wrong_kind_ref`, the single taxonomy-side occurrence, reached by
both `check` and `_require_ref` (and therefore by `update_term` and `add`).
Line 1701 is `FsCapabilitiesStore._check_feature` — a different class, a
different message shape (`Feature → ref …`), pre-existing and untouched; the
criterion scopes itself to `FsTaxonomyStore`, which is why the count is 2 rather
than 1. The one deviation from the criterion's letter: `_wrong_kind_ref` is a
module-level private function sitting immediately above the class rather than a
method inside it, matching the file's existing idiom (`_safe_store_id`,
`_normalize_taxonomy_kind`). Nothing about the "exists once" property changes.

## What the spec and plan got wrong

Each is corrected in place in `spec.md` / `plan.md` with a `> **Correction
(implement).**` block.

1. **"The two callers differ only in output shape"** (spec Design §1, plan task
   2) — they differ in **wording** as well, and both wordings are test-asserted:
   `check` says `dangling vocabulary ref '<r>'`, `update_term` says `vocabulary
   ref '<r>' does not resolve` (`tests/test_taxonomy.py:211`,
   `tests/test_store_editor.py:564`). A helper returning a ready-made message
   would have had to change one of them, breaking task 2's no-behavior-change
   contract. So `_ref_problem` returns a **classification code** and each caller
   renders it. Only the wrong-kind sentence is byte-identical in both callers,
   and it is the one thing shared verbatim — which is also what keeps `points to`
   to a single occurrence for criterion 9.
2. **The item's `capabilities.yaml` did not exist.** The spec says "Record both
   as `changed:` … at plan time"; planning never wrote the file. Implementation
   created it (`f9fcdcd`). Without it the `complete` gate has no record of this
   item's product delta.
3. **Plan task 4's "possibly `tcw/taxonomy/cli.py` error rendering"** — not
   needed. `_add` (`tcw/taxonomy/cli.py:80`) already catches `ValueError` and
   prints `tcw taxonomy add: <message>` to stderr with exit 1; every message in
   verification 1 is that path, unmodified.
4. **Unlisted fallout: four tests built an invalid Feature through `add`.**
   Neither spec nor plan anticipated that criterion 4 makes that construction
   impossible. `tests/test_validate.py` (×2, via a new `_vocabless_feature`
   helper) and `tests/test_validate_target.py` now write the node directly —
   which is what they were actually testing, since their subject is `check`
   reporting it. `tests/test_serve_write.py::test_saved_object_problem_is_a_warning`
   needed a different subject entirely: it asserted that a POST creating a broken
   object returns 201 *with a warning*, and a broken Feature is exactly what is
   no longer savable. It now uses a `Partial` capability with no `Gaps` (an
   object that still saves and still fails `check`), and gained a sibling test
   asserting the new 422-and-no-folder behavior. No assertion was weakened.

## Notes

- **`add` is marginally stricter than the spec's letter, deliberately.** It
  validates `--vocab` refs whenever they are supplied, including on a
  `--kind vocabulary` entry, whereas `check` only validates them on a Feature.
  Writing an unresolvable ref onto a Vocabulary term is silently ignored by
  `check` today, so accepting it at the write boundary would store a ref nothing
  ever looks at. Enforcing it costs one fewer conditional and cannot reject
  anything that was meaningful. If this is unwanted, gate the comprehension in
  `add` on `kind == "Feature"`.
- **The read/write asymmetry now has three statements** — the SKILL.md judgment
  bullet, the release note, and the `add-a-term` capability body — because it is
  the thing a user will trip over: `--vocab zeta` works, `tcw taxonomy show zeta`
  does not. The spec's Risks section predicted exactly this question.
- **GitHub issue #10 stays open**, per the plan's Notes and the user's
  2026-07-30 decision: close it after the containing minor version is cut and
  pushed.
- **Follow-up filed:**
  `docs/work/backlog/2026-07-30-validate-capability-subject-and-feature-refs-at-write-time`
  — `tcw capabilities set --field Subject=/Feature=` has the identical
  write-time gap. Its `initial-request.md` carries the reproduction, the reason
  it could not be folded in here (`FsCapabilitiesStore` holds no taxonomy handle,
  so the fix is a store-composition design question), and a pointer to this
  item's helper as the shape to reuse.
- **Concurrency note for the verifier:** other sessions committed to this repo
  while this item was implemented (`tcw/store/project.py`,
  `tests/test_project_registry.py`, and a `docs/work/` completion). Every stage
  here staged files by name; the seven commits listed above contain only this
  item's files.
