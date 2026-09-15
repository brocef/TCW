# Refined outcome: separate lifecycle stage information from stage prompts

**Accepted** on 2026-09-10, verified against `f355e02` on
`feat/stage-gate-and-prompt-verbs`.

## The decision

Accepted with known defects left unfixed, deliberately. The defects are recorded
in `docs/work/inbox/2026-09-10-verification-findings-on-the-stage-verb-branch.md`
and none of them is this item's.

## Evidence

Verification was delegated to a read-only agent and every finding it returned was
re-checked by hand against the working tree.

| Check | Result |
| --- | --- |
| `pytest -q` | 2450 passed, 0 failed, 0 skipped |
| `tcw validate` | exit 0 |
| `tcw capabilities check` | exit 0 |
| Acceptance criteria | 15 of 16 hold; criterion 8 fails literally |

Fifteen criteria hold. Where a criterion names the `tcw work stage inbox`
spelling, the guarantee holds under `tcw work stage prompt inbox` and
`tcw work stage gate inbox`. All seven built-in prompts ship and resolve; `inbox`
still runs with no work item reference and still refuses one; in a scratch node
created with `tcw init work --id scratch` and no lifecycle configuration,
`tcw work stage prompt inbox` exits 0 and prints byte-identical output to this
repository's. That is the case the item exists to fix and it holds.

Every relative Markdown link under `skills/`, `commands/` and `agents/` resolves:
50 checked, 0 dangling. The criterion 11 grep also prints nothing, so both the
weak check the spec promised and the strong check `outcome.md` describes are
clean.

## Corrections to `outcome.md`

`outcome.md` stands as the record of what was true at its own commit. Three of its
claims are not true at HEAD.

- **Criterion 8 is scored `Pass — 7 of 7` for a sentence that no longer exists.**
  The literal string it required is absent from all seven stage documents,
  replaced by `bac46a2` and then `1ecce6a`. The goal behind it — that every stage
  document instructs rather than describes — survives, and is now enforced by a
  stronger test than the criterion asked for:
  `test_every_stage_document_names_the_harness_neutral_binding_command` requires
  **both** verbs in each of the seven routers. The item's "Superseded within the
  same release" section names only the verb change and should have named this.
  This is why the criterion is called a literal failure and a substantive pass.
- **`2184 passed, 5 failed` is not reproducible.** The suite is clean here. The
  diagnosis was right: four were artifacts of a container running as uid 0, where
  `chmod`-ing a directory read-only does not stop root writing to it, and the
  fifth was a Debian-patched setuptools. `test_the_prompts_are_in_the_built_wheel`
  passing on this machine directly verifies the packaging claim the item had to
  check by hand.
- **`SKILL.md` is 59 lines, not 60.** A sibling edit reclaimed one. Still inside
  budget.

Criterion 13 is confirmed met. `tcw validate` exits 0, so the item's closing
status note is accurate and its earlier "cannot be met by this item" finding is
correctly superseded.

## Capability reconciliation

`capabilities.yaml` declared `work/run-a-lifecycle-stage` as changed, with the
rewrite deferred to completion because shipping a built-in `inbox` prompt
falsified two claims in it. That rewrite landed in `81623de` and is verified
correct: the description now says all seven stages ship a default and that what
`inbox` refuses is a *reference*, on either verb. The deferral is discharged.

## Deferred

One defect touches this item's surface without being its fault, and is filed
rather than fixed:

- The removed-form migration message hands every stage the same `<slug>`
  placeholder, so `tcw work stage inbox` advises a command that is itself refused
  because `inbox` takes no reference. It costs a user on the old spelling two
  wrong turns before reaching what works. It falls in the gap between item 2's
  criterion 5 and item 4's criterion 6, so no criterion covers it.

## Closeout

- **Merge route:** merged locally into `main`, no pull request. The user's call.
- **Version:** 2.0.0 not cut at completion. The cut follows the completion of all
  four items on this branch and is offered separately.
- **Originating issue:** none. This item did not come from a GitHub issue, so that
  Definition of Done criterion does not apply.
- **Post-mortem:** not run. Verification surfaced nothing that warrants one for
  this item.
