# Refined outcome — Generalize the store declaration to taxonomy and capabilities

**Accepted.** All eleven acceptance criteria hold, and the defect verification
found was fixed before submission rather than deferred.

## The decision

The requester's original ask covered all three component trees. Child A
delivered the work store; this item is the rest of that sentence, and it is now
true: a checkout that cloned only the code repository can declare, obtain, and
read a taxonomy or capabilities tree that lives somewhere else.

## Evidence

Every criterion was walked from a bare shell against a real fixture — a bare
orchestrator remote holding a taxonomy tree with one term, and a separate code
repository declaring it **with no `docs/taxonomy/` of its own**, which is the
requester's actual shape and the case the old code could not see.

| # | Criterion | How it was checked |
| - | --------- | ------------------ |
| 1 | declared unprovisioned tree is never "absent component" | 8 commands parametrized; plus the no-local-folder case, which is the only one that reaches the real defect |
| 2 | provisioned is indistinguishable from local | `tcw taxonomy list`, `show <term>`, `path` against a provisioned tree |
| 3 | idempotent, contacts nothing | `GIT_TRACE=1` showed no clone or fetch; "already available", exit 0 |
| 4 | a local store wins, per component | parametrized over all three, with the adapter's Git call intercepted |
| 5 | components provisioned independently | one good declaration and one naming nothing; the good one landed, the bad one was reported, neither result was the other's |
| 6 | nothing configured behaves as today | rule-4 tests including a node with no `docs/taxonomy` at all; no test outside the provisioning module rewritten |
| 7 | failure leaves nothing behind, per component | a tree `repository.path` naming nothing refused with no checkout published |
| 8 | only `tcw provision` reaches the network | `tests/test_subprocess_stdin.py`, unchanged |
| 9 | malformed declaration names the line, per component | 16 cases — both config shapes across the command surface |
| 10 | the Feature rename dangles nothing | `tcw validate`, `tcw capabilities check`, repository-wide grep |
| 11 | reproducible from a bare shell | every row above; no hook, no slash command |

**Suite: 2123 passed**, no failures, no skips. `tests/test_store_provisioning.py`
holds 138 cases, up from the 74 child A left.

The two reader-only checks the plan assigned both hold:

- **The abstraction seam survived the widening.** `StoreProvisioner` still exposes
  only `describe`, `is_available` and `ensure_available`, and no signature names a
  URL, a ref, a directory, **or a component**. The one place the filesystem shows
  through is what "usable" means, and that sits inside the adapter behind an
  abstract predicate — where the litmus test says it belongs.
- **Rule 4 is genuinely unchanged.** Read as code rather than inferred from green
  tests: with nothing configured, `must_exist` is false, `_open_at` validates
  nothing, and the store is built over `docs/<component>` whether or not it
  exists — the one expression it replaced.

## What verification changed

`a99592f`, before submission. Criterion 9 was written as a property and every
test for it set `<component>.path`; without one, the same config still answered
`no tcw taxonomy node here — run \`tcw init\``. A malformed declaration parses to
`(None, problems)`, so the ladder saw no declaration, took rule 4, and a tree
store's rule 4 cannot fail — so the problems were dropped on a code path that
never raises. Details and the fix are in `outcome.md`.

## Closeout choices

- **Route.** Direct to `main`; eleven commits from `0b4c7c0` to the outcome.
- **Documentation.** README, changelog, release notes, and three skill documents,
  all into `upcoming.md` rather than `v1.1.0.md` — that version is now tagged, so
  this work belongs to the next one. Committed separately in `87a39ab`.
- **Capabilities.** Four new, now `Supported`. Five `changed:` bodies genuinely
  edited in `a0178d6` — checked by reading their git history, not by trusting the
  declaration, because child A declared three and edited none.
- **Version.** Offered at closeout, not taken here: child C is still open and the
  epic has not closed. Deferring keeps the initiative's work in one release rather
  than splitting it across two, and avoids a third premature cut.

## Follow-up filed

`tcw work complete` enforces capability reconciliation only for `new:` paths — it
refuses a `new:` capability still reading `Missing`, and checks that every
declared path resolves, but never checks that a `changed:` capability was
actually edited. Child A declared three and changed none, and completed cleanly.
Both times it was caught by hand at `verify`; a third item should not depend on
that. Filed as its own backlog item.

## Still deferred

The post-mortem on the enumeration-versus-property pattern. It has now appeared
four times across two items — and once inside this item's own fixtures, after its
spec was written specifically to prevent it. That is the strongest evidence yet
that stating a criterion as a property is not sufficient, and it is worth
resolving before child C writes acceptance criteria for publish-to-remote
semantics, which is the riskiest surface in the initiative.
