# Plan — Reconcile `read_artifact` with the canonical presence rule

Four tasks, and the ordering rule is unusual because **the test must be written
and passing before the docstrings change**. It is a characterization test: it
records behavior that already exists, so it going green on an untouched tree is
the evidence that it describes today rather than tomorrow. Written afterwards, it
would only prove the docstrings match themselves.

No behavior changes in this item. If the suite moves by anything other than the
one test task 1 adds, something is wrong.

## Tasks

### 1. The characterization test, on an unmodified tree

**Creates:** a test in `tests/test_work.py`
**Modifies:** nothing else

One test, one whitespace-only artifact, all four measured facts asserted
together — because the point is the *disagreement*, and four separate tests would
let three keep passing while the fourth is "fixed":

```python
st.write_artifact(slug, "spec", "   \n\n")
# artifacts()               → spec absent
# read_artifact()           → a resource, with a non-empty revision
# get_detail()              → artifact_revisions contains "spec"
# write_artifact(rev="")    → StaleRevision
```

Its name and docstring say the split is **intended**, so a future reader who
finds it has to argue with a stated decision rather than guess whether it is a
latent bug someone forgot.

**Proves it:** acceptance criterion 4. It must pass on the tree as it stands —
that is what makes it a characterization rather than an assertion.

**Commit:** `test: pin the two artifact-presence rules against each other`

### 2. Prove the test would catch a change — then revert

**Modifies:** nothing that survives the task

Change `read_artifact`'s `p.is_file()` to `self._present(p)` locally, run the
test, watch it fail on the `read_artifact` assertion, revert. This is acceptance
criterion 5 and it is **not** committed: it is a mutation check whose only output
is the observation, which goes in `outcome.md`.

A characterization test that has never been red is exactly as untrustworthy as a
feature test that has never been red.

**Proves it:** acceptance criterion 5.

**Commit:** none — the observation is recorded in `outcome.md`.

### 3. State both rules where an adapter reads them

**Modifies:** `tcw/store/base.py`, `tcw/store/fs.py`

`tcw/store/base.py`:

- `artifacts` (`:1316-1317`) — presence means the artifact holds non-whitespace
  content; a file that exists but is blank is **absent**.
- `read_artifact` (`:1492-1497`) — `None` means no resource at that name; an
  artifact that exists but is blank **is** returned, and `artifacts()` reports it
  absent. The two answer different questions.
- `read_sidecar` (`:1531-1536`) and `read_plan_stage` (`:1335-1336`) — one
  sentence each: same resource rule as `read_artifact`.

`tcw/store/fs.py`:

- `_present` (`:2219-2222`) — stop calling itself "the one presence rule". Say
  which question it answers, and that the read/write/revision surface
  deliberately answers a different one. **Do not enumerate its callers** — a
  docstring listing call sites rots the first time one moves, and the semantic
  boundary is the durable part (acceptance criterion 3).
- `read_artifact` (`:3479`) — one comment at the `is_file()` test pointing back,
  because that line is where the next reader will be standing.

**Proves it:** acceptance criteria 1, 2, 3, 7.

**Commit:** `docs: state both artifact-presence rules on the store interface`

### 4. Documentation Sync

Evaluated against this repo's four entries. **One fires, and it is a judgment
call rather than a reading of the trigger table.**

| Entry | Trigger | Fires? | Why |
| ----- | ------- | ------ | --- |
| `README.md` | Public-API | **No** | The README documents the `tcw` CLI and its user-facing behavior. Neither changes: no verb, flag, output, or exit code moves. |
| `docs/release-notes/upcoming.md` | Public-API | **No** | Nothing a user can observe changes. A release note saying "we wrote down a rule we already followed" is noise in a document whose audience is end users. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **Yes — argued** | See below. |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **No** | No component's CLI surface, model, lifecycle, or guardrails change. Checked against all three skills, not just `tcw-work` — the entry path is a pattern, which the sibling stdin item learned the hard way. |

**Why the changelog fires, when the trigger arguably says it should not.** The
trigger explicitly does *not* fire for "cosmetic-only edits (formatting,
whitespace, comments…)", and docstrings are comments. Read literally, this item
changes nothing that qualifies.

Read for purpose, it does. The changelog's audience is "developers
(contributors, dependents)", and this changes what an implementor of the
`WorkStore` interface is *required to do*: a Jira adapter written yesterday could
have made `artifacts()` report a blank field as present and been within the
documented contract. After this, it cannot. A new obligation on every future
adapter is not cosmetic, even though no runtime behavior moves.

Recorded as a judgment rather than a lookup, with the counter-argument stated, so
that a reviewer who disagrees can see exactly what was decided and reverse one
line.

**Modifies:** `docs/changelogs/upcoming.md`

**Commit:** `docs: changelog for the artifact-presence contract`

## Verification

1. **The exact test count.** 1623 passed today (measured after the sibling stdin
   item landed), so this item must produce exactly **1624** — its one new test
   and nothing else. A floor would hide a test lost to a docstring edit breaking
   a doctest-style assertion; an exact number will not.
2. **`git diff` contains no executable change.** Every hunk under `tcw/` is
   inside a docstring or comment. Read the diff and confirm it by eye — no
   automated check distinguishes a docstring edit from a behavior edit reliably,
   and this item's entire premise is that there is no behavior edit.
3. **The mutation check actually failed.** Task 2's whole value is the
   observation; a plan step whose result is never reported is a step nobody can
   audit.
4. **`tcw validate` and `tcw capabilities check` stay clean.**

## Notes

- `tcw work start` runs **after** this plan is committed and before the first
  code edit — `spec` and `plan` are legal only in `backlog`. The sibling stdin
  item got this wrong and has been carrying a note about it since; this one does
  not have to repeat it.
- No `--blocked-by` links.
- Self-review against the spec: criterion 4 → task 1; 5 → task 2; 1, 2, 3, 7 →
  task 3; 6 → Verification 1 and 2. Every task traces back: 1→c4, 2→c5, 3→c1/c2/
  c3/c7, 4→the Documentation Sync gate. **No task is needed for the follow-up the
  spec names** (the web app showing a blank artifact as present with no
  indication the stage has not run) — that is filed as a separate item at
  completion, deliberately, because it is a `tcw serve` UI change and this item's
  premise is that no behavior moves.
