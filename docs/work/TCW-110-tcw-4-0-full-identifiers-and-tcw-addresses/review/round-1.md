---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-110

Reviewed by a separate read-only agent (the `tcw:reviewer` agent), which did
not write the code, on 2026-10-23 at `c1b1046d`, over
`426c3a3f~1..c1b1046d`. The dispatching session checked the findings against
the repository before writing this round.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session at `c1b1046d`: `5737 passed, 114 skipped in
  532.02s`, the same as implement's run at `89e6bd44`.
- The web client: `pnpm test` (`Tests 187 passed (187)`), `tsc --noEmit`
  exit 0, `pnpm lint` with no warnings, `pnpm check:build` clean, and
  `prettier --check` over the 54 changed files clean.
- The item's 25 main test files, in small groups: all pass. Run as one
  command they gave `625 passed, 20 skipped, 161 errors`, every error a
  fixture not found at setup in `tests/serve/test_records.py`,
  `tests/serve/test_work_write.py`, `tests/work/jira/test_jira_list.py` and
  `tests/work/jira/test_jira_validate_remote.py`. No assertion failed, and
  the full run is green, so this depends on how pytest is given the files
  (finding 6).
- The released `tcw validate`: `0 errors, 0 warnings, 0 unresolved`.
  `.venv/bin/tcw validate` gives 327 errors, all this repository's own 3.x
  links and its root `tcw-config.yaml`, which the spec leaves to TCW-116.
- `documentation-sync`, through `tcw work docs`: both `upcoming/` files are
  written. README, `docs/guide/jira.md`, the other guide pages, the skills,
  `skills/configure/references/` and `docs/use-cases.md` fire and are
  deferred to TCW-117, as the spec's non-goals allow; implement's note giving
  what each must say has been posted on TCW-117's ticket.

## Acceptance criteria

| AC | Result | Evidence |
|---|---|---|
| 1 | met | `tests/test_ids.py`; `tcw/ids.py:171-224` |
| 2 | met | `tests/test_ids.py`, `web/client/src/model/identifier.test.ts`, `tests/fixtures/tcw-addresses.json` |
| 3 | met | by hand: `tcw://C/…`, `tcw://W/…`, `tcw://core/T/…` each report a 3.x reference and `tcw migrate` |
| 4 | met | by hand, full identifiers in every list; inherited case in `tests/test_tree_full_identifiers.py` |
| 5 | met | by hand, `full-id:` then `owner:` first |
| 6 | met | by hand, `"schema": 2`, `full-id`, `owner`, no `slug` |
| 7 | met | by hand, the three forms; wrong namespace exit 2; `demo/<folder>` exit 4 |
| 8 | met | by hand in `item.yaml` and the records; `test_ac8_a_web_edit_stores_the_full_identifier_of_a_reference` |
| 9, 9a | met | `tests/work/jira/test_jira_full_identifiers.py` |
| 10 | met | by hand, exit 4 naming the key |
| 11 | met | `test_ac11_validate_reports_a_3x_value_naming_the_field_and_tcw_migrate`; `tcw/work/gates.py:365-368` |
| 12 | met | `tests/work/test_gates.py:285-298` |
| 13, 13a | met | `tests/test_links_full_identifiers.py:86-110`; `tests/test_tree_full_identifiers.py:117-123`; by hand with a sibling project |
| 14 | met | by hand, `tcw://workspace.path/docs/app/work` |
| 15 | met | by hand, nesting and a loop both refused |
| 16 | met | `tests/test_store_addresses.py:288-328` |
| 17 | met | `tests/test_store_addresses.py:154-164`; by hand |
| 18 | met as written | by hand; the message misses part of Design 1.6 (finding 4) |
| 19 | met | `tests/work/test_full_identifiers.py:147-163` |
| 20 | met | `tests/serve/test_full_identifiers.py`; `reference-search.test.ts` |
| 20a | unit half met; served half not checkable here | the plan gives the board link under `tcw serve` to qa's end-to-end pass |
| 21 | met | a fresh search of `tcw/`, `web/client/src/`, `scripts/`, `evals/` finds no 3.x form; remaining splits are id-paths, disk paths or URLs |
| 22 | met | the suite and web checks above |
| 23 | met | `tests/test_tree_full_identifiers.py:181-191`; `test_ac23_an_extended_owner_routes_to_this_projects_own_ledger` |
| 24 | met | by hand, `/tmp/x` and `~/x` refused |
| 25 | met | by hand, letter case refused naming the folder's spelling |

Handoffs checked: `findings(root)`, `SKIPPED_FOLDERS` and
`MIGRATION_FOLDERS = ()` in `tests/test_identifier_sweep.py:25-46`;
`resolve_work_input(text, active, root)` calls `active()` only for forms b
and d and a form a or c naming the active project (`tcw/work/open.py:103-133`);
no `declared_child_ids()` in `tcw/work/gates.py`; no added git call.

## Capability records

All 16 paths are present and each gained a 4.0 paragraph at its end, but in
nine of them sentences above that paragraph still state 3.x behaviour. That
is a rejection.

1. `work/configure-the-work-store-location`: "using an absolute path or a
   relative one", and `tcw-config.yaml` rather than `.tcw/tcw-config.yaml`.
   An absolute path is refused (AC 24).
2. `taxonomy/configure-the-taxonomy-store-location`: the same.
3. `capabilities/configure-the-capabilities-store-location`: the same.
4. `cli/rely-on-one-output-contract`: lists print "a full item slug, a
   qualified term or capability path"; `"schema": 1`; items named by
   `<project-id>/<folder>`, which now exits 4.
5. `work/read-a-work-item`: `<project-id>/<folder>`, `"schema": 1`, and
   "its slug" as the first field.
6. `taxonomy/read-a-term`: "qualified path", the `shared/invoice` prefix
   form, `"schema": 1`, the ambiguity advice to add a prefix, and a
   tracker-key sentence that does not apply to taxonomy.
7. `capabilities/read-a-capability`: the same pattern.
8. `web/pick-references-and-known-values-from-suggestions:19`: a work item
   is inserted as `tcw://W/<folder>`; the client inserts
   `tcw://<project>.work/<folder>`.
9. `work/declare-capability-changes-in-a-child-projects-ledger`: 3.x example
   entries, the requirement that the child be under `projects.children`, and
   the first-segment and ambiguity rules, all removed by this item.

Weaker: "full slug" in `work/view-the-board`, `work/manage-blocking-relations`
and the `<slug>` placeholders in `work/decompose-a-work-item-into-children`.

The other four records and the five taxonomy entries match the code.

## Further findings

4. Design 1.6 says `show`, `set` and `rm` of a folder that breaks the grammar
   are usage errors naming the rule and the rename. The message names the
   rule but not the rename, offers forms that cannot work for such a folder,
   and says "names no capabilities object" where "capability" is meant.
5. Implement's note for TCW-108 says every `projects:` fixture goes through
   `connect_projects`; the AC 12 fixture at `tests/work/test_gates.py:282-283`
   uses the older `tests.work.projects.connect`.
6. The fixture errors that depend on how pytest is given the files. Not
   caused by an assertion, and the full run is green, but a contributor
   running a list of files can hit it.

## What implement must do

- (a) Rewrite records 1 to 9 so every sentence says what the 4.0 code does,
  replacing the 3.x sentences rather than adding below them, and change
  "full slug" to "full identifier" in the three weaker records. Links inside
  records stay in 3.x form, as the spec requires.
- (b) Make the Design 1.6 message name the rename by hand, without offering
  forms that cannot reach the folder, and say "capability" (and the matching
  word for the other namespaces).
- (c) Switch the AC 12 fixture to `connect_projects`, so the note for TCW-108
  is true.
- (d) Find which file order causes finding 6. Decided by the dispatching
  session: fold it in if the cause is in this repository's test fixtures and
  the fix is small; otherwise record the cause in round 2 and say whether it
  exists before this item.
- (e) Write `implement/round-2.md`, quoting `tests/test_documented_cli_surface.py`,
  the released `tcw validate` and `prettier --check` on the changed records.
