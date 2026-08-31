# Refined outcome — Declare and provision the work store's home repository

**Accepted.** Five review passes; the last one is recorded here.

## The decision

All eleven acceptance criteria hold, verified from a bare shell against a real
two-repo fixture rather than read off the test names. The defect that
verification found was fixed before acceptance rather than deferred, so nothing
known-wrong ships.

## Evidence

Criteria 1-11 were walked by hand in a plain shell — a bare orchestrator remote
holding a work store with one item, and a separate code repository declaring it,
which is the requester's layout:

| # | Criterion | How it was checked |
| - | --------- | ------------------ |
| 1 | board names remote + `tcw provision` | exit 1, both strings present, "no tcw work node here" absent |
| 2 | provision, then the board works | item listed; `tcw work path` printed the provisioned absolute path |
| 3 | second run contacts nothing | `GIT_TRACE=1` showed no clone or fetch; "already available", exit 0 |
| 4 | validate distinguishes the two failures | declared-but-unprovisioned vs. a merely wrong `work.path` |
| 5 | a store already here wins | local item listed; provision reported it without contacting the remote |
| 6 | `--dry-run` contacts nothing | plan printed, no checkout directory created |
| 7 | failure leaves nothing behind | unknown ref, unreachable remote, and a repository carrying no store — all three clean |
| 8 | git stdin closed | `tests/test_subprocess_stdin.py` |
| 9 | `test_external_work_store.py` unmodified | absent from the branch diff; 82 cases pass |
| 10 | malformed declarations refused | four shapes, each reported by `tcw validate`, store never opened |
| 11 | bare-shell reproducible | every row above was a plain shell, no hook, no slash command |

The two checks the epic plan assigned to a reader rather than a test both hold:

- **The abstraction seam.** `StoreProvisioner` exposes `describe`,
  `is_available` and `ensure_available` and no more; no signature names a URL, a
  ref, or a directory. Those live in `RepositoryDeclaration`, a config value
  object, and in the filesystem adapter.
- **The supply-chain posture.** The only `clone` and `fetch` call sites in the
  package are inside the provisioner (`tcw/store/fs.py:2618`, `:2668`), and the
  remote is printed before it is contacted.

Suites: `tests/test_store_provisioning.py` 74 cases, full suite **2057 passed**.

## What verification changed

One defect, fixed in `ddb1edd` before acceptance: a malformed `work.repository`
sent every work command back to `no tcw work node here — run \`tcw init\``. Details
and root cause are in `rework.md`'s fifth pass; the short version is that
`FsWorkStore.open` built the right message and raised a plain `ValueError` that
`find_node` flattened to `None`. `StoreDeclarationError` now carries it.

The capability ledger reconciliation surfaced a second, quieter gap. All three
capabilities listed under `changed:` in `capabilities.yaml` still carried bodies
written before this epic — declared as changed and never updated. The completion
gate reads only `new:` paths, so this would have completed silently with three
capability descriptions contradicting the shipped behaviour. `c2193fb` updates
all three, and the two `new:` capabilities are now `Supported`.

## Closeout choices

- **Route.** Already merged: PR #23 landed as `14f4c71`; the rework commits
  (`dd301af`, `ddb1edd`, `35f950d`, `1fc99a8`, `c2193fb`) are direct to `main`.
- **Documentation.** README, `skills/tcw-work/references/commands.md`, and the
  `v1.1.0` changelog and release notes — written into `v1.1.0` rather than
  `upcoming.md`, because that version is cut in the tree but was never tagged or
  published, so this fix belongs to the same unreleased change set.
- **Version.** `v1.1.0` stays, and gets the git tag it never received. The cut
  itself was premature — made while this item was unaccepted, for the second
  time — but it is merged to `main` and reverting a merged release is worse than
  the violation. Recorded rather than repaired.
- **Follow-ups.** None blocking. Children B and C remain in the backlog under the
  epic, unblocked by this completion.

## Deferred

A post-mortem on the enumeration-versus-property pattern. Three of the five
review passes on this item found the same shape: a criterion written as a list of
examples gets tested to its list rather than to the property the list illustrates
(criterion 7's failure modes, criterion 10's parser cases, criterion 1's command
surface). That is a `spec`-stage defect, not an implementation one, and it is
worth running before children B and C write their own criteria.
