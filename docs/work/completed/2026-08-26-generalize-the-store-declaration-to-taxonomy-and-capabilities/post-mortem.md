# Post-mortem — the uncrossed grid

Scope: one recurring defect across two completed children of
[the store-home-repository epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it).
Filed on child B because that is where the pattern recurred *after* a
countermeasure for it had been written, which is the fact that makes it worth a
post-mortem rather than a note.

## It is not "enumeration versus property"

That was the working name for three review passes, and it is the wrong diagnosis.
Three of the four occurrences are the same two-axis grid, uncovered in three
different cells:

| | `repository` absent | well-formed | **malformed** |
| --- | --- | --- | --- |
| `<c>.path` absent | rule 4 ✓ | ✓ | **occurrence 4** |
| `<c>.path` present, usable | ✓ | ✓ | covered late, by `a99592f`'s inverse test |
| `<c>.path` present, dead | ✓ | ✓ | **occurrences 2 and 3** |

Occurrences 2 and 3 are **the same cell**, found two review passes apart at two
different surfaces — `tcw validate` lost the config problem, and separately the
work commands said `run tcw init`. Nobody generalized the axis after the first
hit, so it was hit again, then hit a third time in the neighbouring cell in a
different item.

Occurrence 1 is a different sub-shape: not a missing cell but a **missing
assertion in a present cell**. Three sibling failure-path tests existed; two
asserted "leaves no directory behind" and said so in their names, the third
asserted only that it raised.

## The fact that indicts the process

**In all four occurrences the uncovered axis was already written down, as a
numbered list, in the same spec's own Design section. Nobody crossed the criteria
against it.**

- **Occurrence 1** — child A's spec numbers the command's steps: step 3 renames
  the clone into place, step 4 *then* verifies the layout. The next paragraph
  asserts criterion 7 and names the rename as what makes it true. Crossing them
  asks one question — "step 4 fails; what is on disk?" — and the answer is the
  published checkout. Visible on paper, with no code and no test.
- **Occurrence 2** — the spec enumerates five error surfaces. Criterion 10 names
  one. Four blank rows.
- **Occurrence 3** — same table, different cell: criterion 1 × the declaration
  states criterion 10 itself introduces. Both criteria are in the same section.
- **Occurrence 4** — child B's Design numbers rules 1-4 and describes rule 4, in
  its own words at `spec.md:124`, as "unchanged and **unguarded**". Criterion 9
  requires a malformed declaration to be named *from every command*. The cell
  (criterion 9 × rule 4) is **unfillable**: an unguarded rule cannot report
  anything. The Risks section even flagged rule 4 as load-bearing — but only in
  one direction, the fear that it would be made too strict. Nobody asked whether
  a criterion required it to be stricter.

Both halves of occurrence 4 were in one document, one section apart, written by
the same author within the same hour.

## Earliest stage that could have caught each

| # | Earliest | What had to be different |
| - | -------- | ------------------------ |
| 1 | **spec** | Cross criterion 7 against the Design's own numbered steps. Second chance at **implement**: the three failure-path tests should share one `_assert_nothing_left_behind()`, so a sibling that skips it is visible. |
| 2 | **spec** | Cross criterion 10 against the five-surface list. Criterion 10 was *true as written* while the behaviour was wrong — rewording it as a property fixes nothing; filling four blank rows does. |
| 3 | **spec** | Cross criterion 1 against the declaration states criterion 10 defines. Second chance at **implement**: parametrize the board test over `[declared_but_absent, declared_but_malformed]` — the second fixture did not exist until the fifth-pass fix created it. |
| 4 | **spec** | Cross criterion 9 against rules 1-4, answering *which code raises* per rule. Second chance at **implement**: `_tree_node` (`tests/test_store_provisioning.py:992`) unconditionally calls `init([component])`, creating the local tree, **and** all eleven call sites pass `path=…`. Two independent narrowings, both from the helper's convenience defaults, which together made the uncovered cell unreachable by construction. |

## Why the previous countermeasure failed

Child B's spec opens its acceptance criteria with a preamble stating that each is
written as a property *because of* occurrences 1-3. It was applied honestly and
the criteria really are general. Occurrence 4 happened anyway.

The narrowing had moved out of the criterion text and into the **test fixtures**.
A general criterion verified by a helper that quietly fixes two of the axes is
indistinguishable, at review, from a general criterion verified generally. Asking
an author "is this criterion general enough?" is unanswerable by inspection.

## The countermeasure

A **cross-product table**, added to `docs/lifecycle/templates/spec.md` under
`## Acceptance criteria`, and two rules in `docs/lifecycle/implementation.md`.
Applied in `<this item's commit>`.

Two properties make it different from the last attempt:

- **The axes are lifted, not imagined.** They come from a numbered list the same
  author wrote in the same document, so there is no judgment call about what to
  vary — only about what each cell contains.
- **A blank cell is countable.** "Row 9, column 4 is empty" is checkable by
  someone who does not understand the feature.

The load-bearing half is that `n/a` must carry the `file:line` proving it. Without
that the table records beliefs, and in all four occurrences the belief *was* the
bug — every one of them would have been written `n/a` in good faith.

Deliberately **not** upstreamed to `tcw/work/prompts/spec.md` yet: that ships to
every TCW user, and this has survived zero items so far. Child C is its first
real test; upstreaming is
[its own backlog item](tcw://W/2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage).

## Honest limit

This catches axes the author already enumerated. An axis nobody wrote down
anywhere is still invisible, and no template fixes that. What is claimed is
narrower: **a spec that contradicts itself across two of its own sections should
not reach implementation**, and all four occurrences were that.
