# Outcome — Declare and provision the work store's home repository

All seven planned tasks landed, each as its own commit, with the suite green at
every boundary. The reported failure is fixed and verified end to end.

## What shipped

| Task | Commit | What                                                                       |
| ---- | ------ | -------------------------------------------------------------------------- |
| 1    | `6eeea2e` | `RepositoryDeclaration`, `parse_repository_declaration`, `StoreNotProvisioned` |
| 2    | `0f3cea4` | `StoreProvisioner`/`ProvisionResult`; `FsStoreProvisioner`                 |
| 3    | `dfa0399` | the resolution ladder in `FsWorkStore.open`                                |
| 4    | `56586a8` | error surfaces; six duplicated strings collapsed into `_require_node`      |
| 5-6  | `d3147b4` | `tcw provision`; the no-implicit-network guard                             |
| 7    | `43c0fca` | README, release notes, changelog, two skills                               |

Plus `63f8a00`, a correction to this item's own spec (below).

## Acceptance criteria

Every one is covered by a test in `tests/test_store_provisioning.py` (59 cases),
and criteria 1, 2 and 5 were additionally walked by hand against a real
throwaway repository pair.

| # | Criterion                                          | Evidence                                                             |
| - | -------------------------------------------------- | -------------------------------------------------------------------- |
| 1 | unprovisioned board names remote + command         | `test_the_board_no_longer_misdirects_to_tcw_init` + 6 parametrized commands |
| 2 | provision, then the board works                    | `test_provision_then_the_board_works`                                |
| 3 | second run contacts nothing                        | `test_a_second_provision_reports_available_and_contacts_nothing`     |
| 4 | validate distinguishes the two failures            | `test_validate_reports_the_declared_store_rather_than_a_dead_path`, `test_without_a_declaration_a_broken_path_still_says_what_it_always_said` |
| 5 | a store already here wins                          | `test_a_store_already_here_wins_over_the_declaration`                |
| 6 | `--dry-run` contacts nothing                       | `test_a_dry_run_from_the_cli_contacts_nothing`                       |
| 7 | failure leaves nothing behind                      | `test_an_unknown_ref_fails_and_leaves_nothing_behind`, `…unreachable_remote…`, `test_a_repository_without_a_store_leaves_no_checkout_behind` (added at rework) |
| 8 | git stdin closed                                   | every call routes through `_git`; `tests/test_subprocess_stdin.py`   |
| 9 | `test_external_work_store.py` unmodified           | untouched in this branch; 82 cases pass                              |
| 10 | malformed declarations refused                    | 9 parametrized parser cases + `test_a_malformed_declaration_refuses_rather_than_doing_nothing` |
| 11 | reproducible from a bare shell                    | the hand walkthrough was a plain shell; no hook, no slash command    |

## Verified by hand

A throwaway orchestrator repository holding a real work store with one item, and
a separate code repository declaring it — the requester's layout. With the
orchestrator absent, `tcw work list` reported the declared remote and
`tcw provision`; `tcw provision --dry-run` printed the plan and fetched nothing;
`tcw provision` obtained the store; `tcw work list` then printed the item;
a second `tcw provision` reported *already available*; `tcw work path` printed
the provisioned location.

## Second pass — external review

An external review of [PR #23](https://github.com/brocef/TCW/pull/23) found two
blocking defects. Both were real, both are fixed, and the details are in
`rework.md`. In short: `_obtain` published the checkout before validating the
store layout, and `_refresh` fetched an existing checkout's `origin` without
checking it against the declaration — so `tcw provision` could print one remote
and contact another.

Both sit in the same blind spot: **the order of publish and validate**, and
**what `exists()` is taken to prove**. Criterion 7 below stated "leaves nothing
behind" but enumerated only the unknown-ref and unreachable-remote cases, so the
tests followed the enumeration rather than the property. Three regression tests
now cover the property; `tests/test_store_provisioning.py` holds 62 cases.

The README, the capability body and the changelog also claimed a failure "leaves
no half-fetched store behind" without qualification — broader than what holds
even after the fix, since a refresh against a pre-existing checkout deliberately
does not delete it. All three now say what is true.

## Suite

6 failures out of 2045 on the final run, all confirmed **pre-existing or
environmental** against a clean-tree baseline of the same tests: two
`test_generate_hook` process cases, `test_scaffold`'s unwritable-target case and
both `test_store_editor` permission cases (all four assume a non-root user; this
container runs as root), and `test_shipped_prompts`'s wheel build (no network).
An earlier run also showed a `test_work_autocommit` case failing on a transient
`signing server returned status 503` from the environment's commit-signing
service; it passes in isolation and did not recur. No test failed because of this
change.

## Decisions worth carrying forward

- **A declaration is a fallback, never an override.** Resolution prefers a store
  that is already present, so the same config works untouched on a machine that
  has the folder. This is what makes the feature additive rather than a
  migration.
- **`_has_work_store` does not propagate `StoreNotProvisioned`** — a correction
  to this item's own spec, made during implementation and committed separately
  (`63f8a00`). It asks about *other* nodes, so propagating would fail a parent's
  topology listing because one child was unprovisioned. `find_node` asks about
  *this* node, which is where the reported symptom lived.
- **Provisioning stays explicit.** The verb is the only network path, and the
  guard in `test_no_read_command_provisions_implicitly` is what keeps it that
  way: it makes the fetch path fatal and runs the commands a user reaches for
  first.

## Found and fixed in passing

Two defects surfaced that were not in the original report:

1. **The message was unimprovable in one place.** `"no tcw work node here — run
   \`tcw init\`"` was written out at six call sites in `tcw/work/cli.py`. That is
   why a store configured elsewhere but absent gave advice that would scaffold a
   second, empty store beside the real one. Collapsed into `_require_node`.
2. **The documented-CLI-surface guard forbade the documented planning
   workflow.** `tests/test_documented_cli_surface.py` failed any capability body
   naming a verb the CLI lacks — but `skills/tcw-capabilities/SKILL.md` requires
   seeding a capability `Missing` at the `plan` stage, and a capability that adds
   a CLI verb necessarily describes one that does not exist yet. The carve-out is
   keyed to an explicit `Status: Missing` and is self-healing: the completion
   gate refuses a `new:` capability still reading `Missing`, so flipping it to
   `Supported` re-arms the guard exactly when the verb must exist.

## Left for the other children

Untouched here, by design: `FsTreeStore.open` still hard-codes
`node_root/docs/<component>` (child B), and nothing writes to a remote (child C).
`declared_repository` and the `--component` flag are already component-generic, so
child B adds callers rather than a parallel mechanism.

`tcw serve` opens `FsWorkStore` per request, so on an unprovisioned node it will
surface the error per route rather than at startup. Legible, but not designed —
worth a look when child B touches the same surfaces.

## Not yet done

The two new capabilities are still `Missing`. They flip to `Supported` at
`tcw work complete`, per `capabilities.yaml`.
