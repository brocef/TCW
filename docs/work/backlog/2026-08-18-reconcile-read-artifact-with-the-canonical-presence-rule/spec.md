# Spec — Reconcile `read_artifact` with the canonical presence rule

## Capability changes

**None.** No user-visible behavior changes. This settles an unstated contract in
the storage-abstracted interface and pins it with a test; nothing a user can do
becomes possible, impossible, or different. Nothing to reconcile at completion.

## Problem

The request is accurate: TCW has two answers to "does this artifact exist", and
they disagree on a file that exists but holds only whitespace.

`FsWorkStore._present` (`tcw/store/fs.py:2218-2222`):

```python
@staticmethod
def _present(p: Path) -> bool:
    """The one presence rule: exists and non-empty. Mere existence would let
    an empty file claim its stage ran, which is what `intake` made visible."""
    return p.is_file() and bool(p.read_text(encoding="utf-8").strip())
```

`read_artifact` (`tcw/store/fs.py:3479`) uses a bare `p.is_file()`.

**Measured, not reasoned.** A scratch node with a `spec.md` containing only
`"   \n\t\n"`:

| Surface | Answer |
| ------- | ------ |
| `artifacts()` → `spec.present` | `False` |
| `read_artifact(slug, "spec")` | a resource, `revision='743b2cb5fa591d16'` |
| `get_detail().artifact_revisions` | contains `spec` |
| `write_artifact(..., revision="")` | **`StaleRevision`** |

### The sweep changes the answer

The request asked for a repo-wide sweep of `is_file()` on artifact paths before
deciding. It does not find one stray call — it finds that **every read/write/
delete/revision surface uses `is_file()`, and only the three lifecycle-presence
surfaces use `_present`**:

| Rule | Surfaces |
| ---- | -------- |
| `_present` (non-whitespace) | `_resolve_body` `:2230`, `artifacts()` `:2255`, `update_work` `:3350`, `write_draft` `:3534` |
| `is_file()` (mere existence) | `read_artifact` `:3479`, `write_artifact` `:3500`, `delete_artifact` `:3548`, `get_detail` artifact + sidecar revisions `:3200,:3207`, `read_sidecar` `:3560`, `write_sidecar` `:3599`, `read_plan_stage` `:2381`, `write_plan_stage` `:2392`, `delete_plan_stage` `:2403`, `PlanStage.present` `:2366`, `_declared_plan_stages` `:2305` |

Twelve to four. This is not an oversight in one function; it is two rules
answering two different questions, one of which was never written down.

**The request's own list of `_present` callers was wrong, and correcting it
strengthens the conclusion.** It named "`artifacts()`, `_resolve_body`, and
`body_path`". `body_path` (`fs.py:2236-2241`) does not call `_present` at all —
it delegates to `_resolve_body`, so it inherits the rule rather than applying it.
The two callers the request missed are the interesting ones, and both are
lifecycle judgments rather than resource lookups:

- **`update_work` `:3350`** computes `had_request = self._present(body_path)`,
  which decides whether a body write *promotes* the item — i.e. whether this edit
  is the one that created the request. A whitespace-only `initial-request.md`
  must not count as "already had a request", or the promotion is never reported.
- **`write_draft` `:3534`** guards `<artifact>.draft.md` against clobbering:
  `if not force and self._present(p)`. A blank draft is not something worth
  refusing to overwrite.

Both would be *wrong* with `is_file()`, exactly as the twelve would be wrong with
`_present`. The split is not accidental; it is applied correctly at six separate
decision points by two different authors.

### Why they must differ — the deciding evidence

Adopting `_present` in `read_artifact` **breaks the optimistic-concurrency
protocol**, and this was executed, not argued:

1. `read_artifact` returns `None`, so a client concludes the artifact has not
   been written.
2. Per `write_artifact`'s own contract (`tcw/store/fs.py:3506-3511`), "does not
   exist yet" means send `revision=""`.
3. `write_artifact` still tests `p.is_file()` (`:3500`), sees the file, computes
   its revision, and raises `StaleRevision: expected '', got 743b2cb5…`.
4. The client cannot recover: the only surface that yields the right revision is
   the one now returning `None`.

A read that says "absent" while the paired write says "stale" is a deadlock. The
escape would be to change `write_artifact`, `delete_artifact`, `get_detail`, both
sidecar methods and all four plan-stage methods to agree — twelve surfaces — and
the result would silently overwrite a file the caller never saw. That is a much
larger and worse change than the one being contemplated.

It also destroys a legitimate operation the request itself anticipated: **reading
a file in order to see that it is blank.** With `_present`, a blank artifact is
unreadable, unversioned, and indistinguishable from one that was never created —
while still occupying the path.

### So what is actually wrong

Not the behavior. **The contract**, in the one place a non-filesystem adapter
would read it:

- `WorkStore.artifacts` (`tcw/store/base.py:1316-1317`) — "The bounded lifecycle
  artifact set for `slug`, with presence only." It never says what presence
  *means*, so a Jira adapter cannot know that a whitespace-only description must
  report `present=False`.
- `WorkStore.read_artifact` (`tcw/store/base.py:1492-1497`) — "Returns `None`
  when the artifact has not been written yet." Ambiguous on exactly the case in
  question: a blank file has been written.
- `_present`'s docstring calls itself "**the one** presence rule" while eleven
  other surfaces use a different one — actively misleading to the next reader,
  which is how this item got filed.

Two adapters reading these docstrings today would diverge, and nothing would
catch it.

## Goals

1. Record the decision: the two rules differ **deliberately**, and say which
   question each answers.
2. State both rules in the abstract interface, so an adapter implements the same
   split rather than guessing.
3. Pin the split with a test, so a future "consistency" fix has to argue with a
   red suite instead of a comment.
4. Change no behavior.

## Non-goals

- Changing which rule any surface uses. The measured deadlock says the current
  assignment is right.
- Unifying sidecars or plan stages onto `_present`. Same reasoning, same verdict.
- Preventing whitespace-only artifacts from being written. `write_artifact`
  accepts any text by design, and rejecting blank content is a different
  decision with its own callers.
- Auditing `is_file()` calls outside the work store's artifact/sidecar/plan-stage
  surfaces (`validate.py`, `serve/runtime.py`, node discovery). Different
  question, not artifact presence.

## Design

### Name the two questions

| Question | Rule | Meaning |
| -------- | ---- | ------- |
| *Did this stage produce anything?* | `_present` — exists and has non-whitespace content | A lifecycle judgment. Drives the board, `tcw work show`, the `iRSP` flags, and body resolution. A blank file must not let a stage claim it ran. |
| *Is there a resource at this name?* | `is_file()` — mere existence | A CRUD fact. Drives read/write/delete and the revision tokens that make concurrent editing safe. A blank file is a real resource: readable, versioned, deletable. |

Three edits, all documentation, plus one test:

1. **`tcw/store/base.py`** — `artifacts()` gains the presence rule explicitly
   ("present means the artifact holds non-whitespace content; a blank one is
   absent for lifecycle purposes"), and `read_artifact` gains the resource rule
   plus the cross-reference ("`None` means no resource at that name — an
   artifact that exists but is blank *is* returned, and is reported absent by
   `artifacts()`; the two answer different questions"). One sentence on
   `read_sidecar` / `read_plan_stage` pointing at the same rule.
2. **`tcw/store/fs.py`** — `_present`'s docstring stops claiming to be "the one
   presence rule" and instead says it is the *lifecycle* presence rule, names its
   four callers, and states that the read/write/delete surface deliberately uses
   mere existence, with the `StaleRevision` deadlock as the reason.
3. **`read_artifact`** gains a one-line comment at the `is_file()` test pointing
   back, since that line is where the next reader will be standing.

### A test, because a docstring does not fail

`tests/test_work.py` gains one test that writes a whitespace-only artifact and
asserts the whole measured table at once: `artifacts()` absent, `read_artifact`
present with a revision, `get_detail` carrying that revision, and
`write_artifact(revision="")` raising `StaleRevision`. It is a **characterization
test**: it fails if either rule moves, in either direction, and its name says the
split is intentional.

### Abstraction litmus test

| Operation | Verdict |
| --------- | ------- |
| Report lifecycle presence of an artifact | **Model** — already on the interface; this only writes down the rule it always had. A tracker adapter answers it from field content. |
| Read an artifact resource | **Model** — already on the interface. "A resource exists at this name" is answerable by any store. |

Nothing moves between layers. The change makes the interface *more* portable: the
rule an adapter must implement is currently discoverable only by reading
`FsWorkStore`, which is precisely the filesystem-detail-leaking-into-the-model
failure the prime directive exists to prevent.

### Harness compatibility

Docstrings and a test in the Python package. Identical under both harnesses.

## Acceptance criteria

1. `tcw/store/base.py`'s `artifacts` docstring states that presence means
   non-whitespace content and that a blank artifact is absent.
2. `tcw/store/base.py`'s `read_artifact` docstring states that `None` means no
   resource exists, that a blank-but-existing artifact **is** returned, and names
   `artifacts()` as the surface that answers the other question.
3. `tcw/store/fs.py`'s `_present` docstring no longer claims to be "the one
   presence rule", names all four of its callers, and gives the reason the
   read/write surface differs.
4. A test in `tests/test_work.py` asserts, on one whitespace-only artifact, all
   four measured facts: `artifacts()` reports absent; `read_artifact` returns a
   resource with a non-empty revision; `get_detail().artifact_revisions` contains
   it; `write_artifact(..., revision="")` raises `StaleRevision`.
5. That test fails if `read_artifact` is changed to use `_present` — verified by
   making the change locally, watching it fail, and reverting.
6. No behavior change: `python -m pytest -q` reports ≥ 1592 passed, 0 failed,
   with no test modified other than the addition in criterion 4. The baseline is
   **exactly 1592 passed in 284s**, measured on this tree today, so "≥ 1592"
   means "no test was lost".
7. `grep -n "the one presence rule" tcw/` returns nothing.

## Risks

- **Documenting a split invites someone to keep adding to it.** Twelve surfaces
  on one rule and four on the other is defensible only while the two questions
  stay distinct. Named ceiling: a *fourth* question ("exists but is blank" as its
  own state) is the trigger to model presence explicitly rather than write a
  third docstring.
- **A characterization test pins current behavior, including anything wrong with
  it.** Accepted deliberately — the deadlock evidence says the behavior is right,
  and the test's name and docstring say what it is protecting so it can be
  changed on purpose rather than by accident.
- **The whitespace-only artifact is still reachable through the web editor**,
  which can save a blank body and produce an item whose board row says the stage
  did not run while the editor shows a file. That is confusing but correct under
  the split, and it is not what this item was filed to fix. Recorded rather than
  fixed.

## Notes

- The request left the decision open — "either answer is defensible" — and asked
  for a sweep before deciding. The sweep and the `StaleRevision` measurement are
  what closed it; without them "adopt `_present`" was the more attractive answer
  and would have introduced a bug.
- Reproduction:
  `/private/tmp/claude-501/-Users-brian-Projects-TCW/2c522064-e54a-48d2-8072-1ff5efdfa137/scratchpad/presence_probe.py`.
  Scratch, not shipped; criterion 4 is it turned into a test in the repository.
- C5's decision to route around this rather than fix it
  (`docs/work/completed/2026-08-12-scaffold-lifecycle-artifacts-from-templates/refined-outcome.md`)
  was correct, and for a better reason than it knew: `artifacts()` is the right
  surface for a stage-presence question regardless of how this item resolved.
- Every `file:line` above was re-resolved against the tree while writing this,
  and again during self-review. That pass corrected the sweep table: the first
  draft repeated the request's three-caller list, and `grep -n "_present"
  tcw/store/fs.py` shows four call sites, one of which (`body_path`) was not a
  caller at all. The two it had missed are the strongest evidence in the spec.
