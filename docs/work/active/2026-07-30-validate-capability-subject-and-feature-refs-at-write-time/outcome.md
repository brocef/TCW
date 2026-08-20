# Outcome — Validate capability Subject and Feature refs at write time

Six planned tasks, plus a seventh commit fixing what an adversarial review of
the finished diff found.

## What shipped, task by task

| Task | Commit | What landed |
| --- | --- | --- |
| 0 | `tests: pin the exact wording of every capability ref problem` | 13 characterization tests, written **before** the extraction |
| 1 | `capabilities: extract _ref_problems, the single ref-problem renderer` | Pure motion; zero test files touched |
| 2 | `capabilities: check falls back to the node's own taxonomy` | `_taxonomy()`, the `is not None` fallback, two duplicate wirings deleted |
| 3 | `capabilities: refuse an unresolvable ref at write time` | The reported fix, six fields, plus the one rewritten test |
| 4 | `capabilities: add takes its fields, so a rejected create writes nothing` | `add(..., fields=)`, abstract signature, POST handler |
| 5 | `capabilities: state at-save ref refusal in the two affected bodies` | The two capability text deltas |
| 6 | `docs: say set resolves ref pointers too` / changelog / release notes | Documentation sync |
| — | `capabilities: fix three defects an adversarial review of the diff found` | See below |

Task 0 is not in the plan by that name — it is Task 1's "characterization tests
first" requirement, split into its own commit so the extraction's diff reviews as
motion against a green, wording-pinned suite.

## Test result

`python -m pytest -q` → **1931 passed**, against a **1859** baseline measured
before any item in this batch. `tests/test_capability_ref_wording.py` is new (40
tests).

Exactly one existing test needed editing, as the plan predicted and for the
predicted reason: `test_capability_check_dangling_subject` built its fixture by
calling `set(..., {"Subject": "ghost"})`, which this change makes impossible. It
was **rewritten, not deleted** — it now writes the invalid node directly and
still asserts `check` reports it, which is what proves data predating the rule
stays reportable and therefore repairable.

## What the plan and spec got wrong

**Found before implementation, by review round 1** (all verified against the tree
before acceptance; the plan carries the corrections):

1. **The "three divergent wirings" claim was false.** The spec presented
   `tcw serve` as a third capability-check wiring that diverged by opening its
   taxonomy store unconditionally. It does construct one unconditionally — but
   never passes it to `capabilities.check`; serve's post-save warnings go through
   `validate()`, the guarded path. Two wirings, not three, and the taxonomy-less
   behaviour was already aligned. Independently re-confirmed by the review of the
   finished diff.
2. **The existing tests do not pin the wording.** The plan asserted the six
   messages were "asserted at `tests/test_capabilities.py:207-256`". Every one of
   those is a *substring* assertion, so "pure motion" was unprotected exactly
   where it mattered. Hence Task 0.
3. **A taxonomy store was opened on every write.** The original text called
   `self._taxonomy()` unconditionally, including for a status-only repair — which
   would have made criterion 11's repair route start failing on a node with a
   malformed taxonomy config. Now conditional on `Subject`/`Feature` being
   supplied.
4. **"POST becomes one write / kills the whole class" overstated it.** It is
   *validation*-atomicity: `_write_node` still stages after writing and keeps the
   files when `git add` fails. Narrowed everywhere it appeared.
5. **A stale blocker.** The plan filed the non-git-writes item as a dependency;
   it is completed and its work is in the tree. The live consequence is the
   opposite of what the plan said — the repository precondition now runs ahead of
   every write, so a write-path fixture that is not a real git repository fails
   at the guard and never reaches the code under test.

**Found after implementation, by the review of the finished diff** — all three
reproduced before fixing, all three fixed in the final commit:

6. **`add(fields={"Status": None})` kept the seeded Status.** The plan reasoned
   "on a node being created there is nothing to clear". There is: the `Status`
   written from the `status` argument one line earlier. `add`-then-`set` popped
   it via `_merge_meta`; the new single write did not. A genuine behaviour change
   on an input the change claimed was byte-identical.
7. **A non-string ref value crashed instead of being refused.** `Subject` and
   `Feature` were passed to the resolver untouched while the other four already
   went through `str()`. `Feature: 1` reached `taxonomy.get`, which calls
   `.partition("/")`, and escaped as `AttributeError` — a 500 through `tcw serve`,
   not the 422 that the changelog, release notes, README, capability bodies and
   skill all promise. Now `str()`-coerced and refused as a dangling ref, matching
   the four fields that always did.
8. **The characterization tests claimed fifteen literals and pinned eleven.**
   The four ambiguous-*identifier* variants were missing, and the file's own
   docstring said otherwise. They need a federated fixture: capabilities are
   path-addressed, so ambiguity means the same path in two *extended* stores,
   never a leaf-slug clash. Added; the docstring now states its coverage
   accurately.

## Abstraction litmus test

Passes, with one deliberate interface change. `_ref_problems`, `_taxonomy` and
the refusal are private to the filesystem adapter. The one abstract change is an
optional trailing `fields` keyword on `CapabilitiesStore.add`
(`tcw/store/base.py`) — backwards-compatible, and *more* natural for a
non-filesystem adapter than create-then-update, since a tracker creates an issue
with its fields in one API call. Judged against the alternative (a new abstract
`validate_fields` every adapter must implement) it is the smaller change, and it
is not opt-in: a caller cannot silently skip it.

## Known limits, accepted

- **Falsy ref values still bypass resolution.** `Feature=""`, `0`, `False`, `[]`
  are skipped by the `if not feature` guard and persist; `Subject=""` normalizes
  to `[]`. Consistent with the pre-existing shape of these checks and not made
  worse here, but a field-shape contract — rather than truthiness — is the real
  answer. Surfaced by the diff review as needing a different mechanism.
- **A taxonomy store is opened per write that supplies `Subject`/`Feature`.**
  Under `tcw serve` a single POST can construct the federated graph three times
  (`_stores`, write validation, post-save validation). No recursion risk —
  `_seen` handles federation cycles — and no measured cliff. Caching is a
  separate optimization that should be measured first.
- **Full atomicity of a create is still not provided.** A staging failure after
  `_write_node` leaves a complete capability on disk. That is the sibling item
  `2026-08-20-a-git-refusal-after-the-filesystem-write-still-leaves-a-partial-write`,
  whose `_write_staged` is exactly the mechanism this one lacks.

## Notes

- **Ordering held.** This item landed after
  `2026-07-30-resolve-taxonomy-refs-against-symlinks-not-just-lexically`, as
  required — both edit `FsCapabilitiesStore.add`. The merged order was verified
  by the diff review: `_safe_store_id` → status check → `d` → `_within_store` →
  `exists()/is_symlink()` → `_validate_fields` → display → `_mint_cap_id` (once)
  → merge → `_write_node`. The containment guard survived intact and correctly
  precedes both validation and minting.
- **Spec Design §6's "function-level overlap: none" is false** — `add` is the
  overlap, and the plan already said so further down. Recorded rather than
  silently corrected.
- **The spec's Reproduction snippet calls `_check_subject` with a `where`
  argument.** After Task 1 that call shape no longer exists. The spec is right
  about the behaviour; the snippet records a pre-extraction call. Left as
  committed.
- **Two dead numbers retired.** The spec's `1763 passed` and the plan's `1772`
  are both stale; the durable claim was always "exactly one existing failure, and
  it is `test_capability_check_dangling_subject`", which held.
