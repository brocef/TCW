# Implement round 1 — TCW-110

Built on the `v4` branch in the worktree `.claude/worktrees/v4`, with the code
under test run from its own virtual environment (`.venv/bin/pytest`,
`.venv/bin/tcw`). The records of Step 16 were written in their 3.x form and
checked with the released 3.x CLI on PATH, which reads this repository's root
`tcw-config.yaml`. This is the first implement round, so it answers no
rejection. It gives no verdict.

## What was done, step by step

- **Step 0 — the starting point** (`426c3a3f`). TCW-106 and TCW-107 are on
  `v4`, TCW-108 is not; `project_folder` and its four answers exist;
  `pnpm install --frozen-lockfile` was run in the worktree. The spec and plan
  were formatted with `prettier`, and the plan's cross-reference to TCW-111's
  length limit corrected. The plan's line citations were not re-checked line
  by line; each was found by searching where the code had moved.
- **Step 1 — the identifier module** (`cca10d2c`). `tcw/ids.py`: `FullId`,
  `FolderAddress`, `parse_full_id`, `parse_address`, `parse_stored`
  (`ThreeXReference` and `MalformedId`, both `IdError`, a usage error),
  `sort_input` (the four input forms a to d), `is_3x_address` and the 3.x
  messages, `SCHEME`. `tests/test_ids.py` (20 tests) and
  `tests/fixtures/tcw-addresses.json`, the cases both parsers share.
- **Step 2 — the web client's identifier module** (`d142bc5e`).
  `web/client/src/model/identifier.ts`, tested over the same fixture and
  against Node's URL parser; `test-setup.ts` guarded for the Node test
  environment.
- **Step 3 — test helpers** (`3b3b16bf`). `tests/fullids.py` (`fid`, `wid`,
  `addr`) and `connect_projects` in `tests/projectfiles.py`.
- **Step 4 — work items** (`83bd5288`). The work model's `Slug` is a full
  identifier; records carry `full-id` and `owner`; `print_json` writes
  `"schema": 2`; a stored 3.x reference makes its item unreadable with a
  message naming `tcw migrate`; the client reads `full-id` and was rebuilt.
  `tests/work/test_full_identifiers.py`.
- **Step 5 — Jira part way through `tcw migrate`** (`173d40e3`). `tcw work
list` leaves out tickets whose `TCW Item` is a 3.x value with one warning
  naming their keys; `tcw validate --remote` reports each once.
  `tests/work/jira/test_jira_full_identifiers.py`.
- **Step 6 — trees printed by full identifier** (`1877e3c0`). Owner and full
  identifier on every entry and capability; list, add, search and show print
  it; the web server routes an inherited entry by its whole full identifier
  and the client keys its tree by `keySegments`. `tests/inherit.py`,
  `tests/test_tree_full_identifiers.py`, `tests/serve/test_full_identifiers.py`.
- **Step 7 — finding the owner** (`141f7461`). `tcw/locate.py` with
  `Locator`, one per registry; tree stores carry the active root on their
  federation walk; `open_project` looks every ID up with `project_folder`.
  `tests/test_locate.py` (17 tests).
- **Step 8 — what commands accept** (`1d98dd88`). `sort_input` at every
  argument and option that names an object; `find_tree` and
  `find_tree_writable`; exact letter case, with the spelling on disk in the
  not-found message; the 3.x hint naming the full identifier to write;
  `--parent` and `--blocked-by` read from their owner before anything is
  written; names breaking the identifier rule refused, and reported by
  `validate`. 28 new tests across the CLI test files.
- **Step 9 — stored references** (`e522a73b`). Every stored reference in a
  term or capability is a full identifier; the web pickers write full
  identifiers. `tests/test_stored_references.py` (14 tests) and AC 8's web
  test.
- **Step 10 — `tcw://` links** (`17896ce8`). `tcw/refs.py` rewritten around
  `resolve_address` and `route_key`; `validate` and `/api/resolve` use it;
  `AXIS_WORD` deleted. `tests/test_refs.py`, `tests/work/test_refs_work.py`
  and the link tests of `tests/test_validate.py` and
  `tests/serve/test_records.py` rewritten; `tests/test_links_full_identifiers.py`
  new.
- **Step 11 — `capabilities.yaml` entries** (`c86f1351`).
  `route_capability_path` names the ledger from the entry's project; the new
  `Invalid` answer; `_LedgerReader`; the web save qualifies an id-path. The
  stores' `get` was deleted, and its 107 test call sites moved to `get_view`
  or `get_inherited`, found by a temporary logging shim that recorded which
  each call needed. `tests/test_routing_nodes.py`, named by the plan, holds no
  `capabilities.yaml` routing and was left alone.
- **Step 12 — relative locations** (`a0bbb98e`). `store_location_problem` in
  `tcw/config.py`; `tcw init` refuses an absolute or `~` location given on
  its command line (exit 2) or already configured (exit 1).
  `tests/test_store_addresses.py` created; fixtures moved to relative paths.
- **Step 13 — folder addresses as locations** (`63ed5ee1`). `store_location`
  and `LocationProjectAbsent` in `tcw/store/fs.py`, placed outside the region
  `tests/test_tree_store_raises.py` guards; loops refused naming the chain;
  `validate`'s `_location_findings`. On the old code 21 of the file's 32
  tests fail.
- **Step 14 — stores never nest or coincide** (`1bb2cd61`). `_store_overlaps`
  replaces `_shared_work_paths`. The old tests in
  `tests/work/test_validate_work.py` now call it with a `Locator` and assert
  the new message; `tests/test_validate_moved_stores.py`'s shared-store test
  now expects the overlap error from each project's run. 7 new tests (AC 15's
  nesting half, AC 16's five cases, the worktree case); on the old code 5 of
  them fail (the sibling and worktree cases pass on both, as they should).
- **Step 15 — the sweep guard** (`18e48069`). `tests/test_identifier_sweep.py`
  in the shape TCW-116 asked for. The plan's split-site search was repeated on
  the finished change: every hit is an id-path, a path on disk, a URL, or the
  identifier modules themselves, as the table says; the two new ones are
  `three_x_hint` in `tcw/locate.py` (the first part of an id-path, to suggest a
  full identifier) and `three_x_item` in `tcw/work/jira/backend.py` (the 3.x
  `TCW Item` recogniser), both reading 3.x text only to report it.
- **Step 16 — records** (`0fa9526c`, formatting `89e6bd44`). See below.
- **Step 17 — notes for later children.** The text is under "Notes for the
  later children" below, for the dispatching session to post.
- **Step 18 — documentation entries** (`5e030380`). See the table below.
- **Step 19 — the suite as CI runs it.** See the end.

## Decisions

Each decided by the implementing agent, the simpler and safer option where
there was a choice.

- **The stored 3.x message names the namespace** of the field it is in, so it
  says which full identifier to write.
- **A multi-part work id-path is not found** (exit 4) until TCW-111 adds
  nested items, rather than a usage error.
- **Some test literals are written out** rather than through `wid`, where the
  literal is the thing under test.
- **`RESERVED_PROJECT_IDS` was not moved**: TCW-107 had already moved it to
  `tcw/project_files.py`.
- **The owner is `""` when a configuration has no `id`**, rather than an
  error, so a malformed project still lists.
- **`ProjectIdContext`** in the client carries the served project's ID, rather
  than passing it through every component's props.
- **`extends` resolution was left as it is**; only lookups by ID go through
  the `Locator`.
- **A project graph error is the `error` answer**, never `unresolved`.
- **A dangling blocker can be removed** with `--unblocked-by` even though the
  item it names does not exist.
- **`--blocks` and web references take a form-a full identifier as written**,
  and its owner is opened when the write is made.
- **A web reference to another project is still kept**, with a warning, as
  3.x did.
- **The web route for another project's entry that is not inherited answers
  404**: the served project cannot show it.
- **The spelling on disk is named on any disk**, not only one that ignores
  letter case.
- **Four stored loose-spelling cases were dropped** from
  `test_remove_refuses_referenced_target` in Step 8: stored references can no
  longer take those spellings.
- **A stored reference cannot be ambiguous**; the ambiguity wording moved to
  the write path, where a typed id-path can be.
- **`update_term` validates only the values the edit gives**, so an entry
  with an old 3.x value elsewhere can still be edited.
- **The Roles wording "must be a roles/ slug" was kept.**
- **With no taxonomy store, a Subject id-path is qualified with the project's
  own ID.**
- **Only own-project references block a removal**; a 3.x value does not.
- **The declaration pickers kept the 3.x form until Step 11**, so each step
  left the client working.
- **A folder address in `/api/resolve` answers inert**, with a detail saying
  it names a folder.
- **`validate` does not repeat the address** at the start of a link message
  that already starts with it.
- **A new `Invalid` answer in `tcw/work/gates.py`**, for an entry whose text
  is malformed or names an unknown project, reported before the finished
  check.
- **`tcw init` also refuses a configured absolute or `~` location** (exit 1),
  and checks a location given on its command line before anything else
  (exit 2).
- **The configuration problem for a refused location omits the key**,
  because the finding's line already names it.
- **Tree-store default anchoring also applies to `init`'s given paths.**
- **`_store_overlaps` reads each project's configuration with `load_config`
  and follows store addresses one level beyond the registry's projects**:
  every project a store location names is added to the projects compared,
  and its own addresses are followed in turn, each project once by ID. A
  project whose configuration cannot be read, or whose location is refused,
  is left out; those are reported at their own keys.
- **`tcw migrate` is named without backticks in the records**:
  `tests/test_documented_cli_surface.py` refuses a backticked command that
  does not exist yet. The plan said the existing descriptions already name it
  that way; they do not name it at all.
- **Three records this item changed were reformatted** (`89e6bd44`); they
  failed `prettier --check` before this item.

## Limitations recorded

- A work location opened for another project without a walk uses
  `Locator.of` that project's root, which can open a second registry.
- A capabilities check may add a second unresolved or error line when the
  taxonomy store's location is unusable.

## Handoffs folded in

- **TCW-116:** `tests/test_identifier_sweep.py` is one function,
  `findings(root) -> list[str]`; skipped folders are one module constant,
  `SKIPPED_FOLDERS`, matched by whole path parts, with
  `MIGRATION_FOLDERS = ()` beside it.
- **TCW-109:** `resolve_work_input(text, active, root)`, done in Step 8.
- **TCW-111:** `exact_child` and `exact_path` stay in `tcw/store/fs.py` for
  TCW-111 to move to `tcw/object_folders.py`.
- **TCW-108:** every `projects:` fixture goes through `connect_projects`; the
  records gate in `tcw/work/gates.py` makes no `declared_child_ids()` call.
- **TCW-107:** a project is unreachable only for an empty folder or one
  holding only `.git`; nothing here changes that.
- **TCW-115:** this item adds no git call. Every `+` line of
  `git diff 426c3a3f~1 HEAD -- tcw` was searched for `subprocess`, `"git"`,
  `_git(` and `_git_lines`, with no match.
- **TCW-112, TCW-113 and TCW-114:** for information only; see the notes below.

## Notes for the later children

- **TCW-108:** every test of this item writes its `projects:` entries through
  `connect_projects` in `tests/projectfiles.py`, so converting them is a
  change to that function's body. The tests that connect projects through the
  3.x `projects:` key: `tests/test_locate.py`;
  `tests/test_links_full_identifiers.py` (AC 13 and 13a);
  `tests/work/test_gates.py`'s AC 12 cases; every fixture using
  `taxonomy.extends` or `capabilities.extends` (`tests/test_tree_full_identifiers.py`,
  the AC 23 cases there and in `tests/work/test_gates.py`, `tests/test_locate.py`'s
  "as `app` sees it" case, `tests/serve/test_full_identifiers.py`'s inherited
  route key); `tests/test_store_addresses.py`'s overlap tests; and
  `_store_overlaps` in `tcw/validate.py`, which lists `ancestors()`,
  `descendants()` and `declared_upstream_ids()`. `open_project` already looks
  every ID up with `project_folder`, so TCW-108's Design 3.7 has nothing left
  to do there, and the 3.x `<sibling>/<folder>` input 3.7 kept readable is no
  longer accepted (spec 3.4).
- **TCW-111:** `TCW Item` is a single-line field of at most 255 characters; a
  nested id-path can pass it. `tcw/ids.py` sets no length limit; the limit is
  TCW-111's to add. `exact_path` already walks an id-path part by part.
- **TCW-112:** the inherited-view rule lives in `tcw/locate.py` (`find_tree`,
  `read`), the stores' `_found`, and `route_capability_path`; the collision
  findings and the `overrides:` pointer were kept for the 3.x override
  folders.
- **TCW-113:** the web route key of every inherited entry is its full
  identifier, URL-encoded, and `/api/resolve` answers `ok` with it as `key`;
  the tree shows such an entry under one top node `<project>.<namespace>`.
- **TCW-116:** report absolute and `~` store paths, names that break the
  identifier rule, 3.x `TCW Item` values, and stores that nest or coincide;
  convert this repository's own links and `capabilities.yaml` files, and its
  ledgers, still in 3.x form; `RESERVED_PROJECT_IDS` still holds the 3.x axis
  letters `t`, `c`, `w`, which the 4.0 grammar no longer needs reserved.
- **TCW-117:** what each deferred document must say: `README.md` and
  `docs/guide/linking-and-validation.md`, the `tcw://` grammar, links to any
  project TCW can locate, and 3.x links needing `tcw migrate`;
  `docs/guide/multi-repo.md` and `skills/configure/references/*`, store
  locations as relative paths or `.path` addresses, absolute and `~` refused
  in the shared file, stores that may not nest or coincide;
  `docs/guide/jira.md`, `TCW Item` holds the full identifier and 3.x tickets
  are left out of `tcw work list` with one warning and reported by
  `tcw validate --remote`; `docs/guide/cli.md`, `docs/guide/configuration.md`
  and `skills/configure/references/work.md`, records carry `full-id` and
  `owner` and every JSON document is `"schema": 2`; `docs/use-cases.md`,
  UC-4's address (`tcw://workspace.path/docs/app/work`) and UC-6's gap closed
  for taxonomy and capability links; `skills/*/SKILL.md`, every component's
  names and input forms; `tcw/work/procedures/pause-work.md:22` and
  `tcw/work/procedures/search.md:27`, which teach bare slugs and
  `<project>/<folder>`.

## Records

With the released CLI, in their 3.x form: the new capability
`cli/name-any-tcw-object-by-its-full-identifier` (`cap-7cafec`, Supported,
subjects `full-identifier` and `tcw-address`, feature `project-registry`);
the fifteen changed capabilities, each description given the sentences the
spec's "Capability changes" names; the new terms `full-identifier` and
`tcw-address`; and the descriptions of `namespace`, `reference` and
`configurable-component-store-location` (which now lists `tcw-address`).
`tcw validate` with the released CLI: `0 errors, 0 warnings, 0 unresolved`.
`tests/test_documented_cli_surface.py` passes.

## Mutation checks

Each mutation was applied to the source, the named tests run, and the source
restored (`mutate.py` in the scratchpad). Every one went red unless said.

- Steps 1 to 13: the new tests were mutation-checked as they were written.
  Four survivors each led to a new test that then went red: the removal
  branch of `Invalid`, a term that is unresolved, the own-project check on a
  removed reference, and the `roles/` folder rule.
- Step 14: not following a store address to its project (red), not adding
  the registry's upstreams (red), not adding ancestors and descendants (red).
- Step 15: `.qualified` put back in `tcw/refs.py` and
  `f"{self.project}/{folder}"` in `tcw/work/model.py`: the guard failed and
  named both files.

## Documentation entries

| Entry                                                                  | Answer                                                                                                                |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `README.md` [Public-API]                                               | Fires. Deferred to TCW-117, which rewrites the user-facing documents for 4.0; what it must say is in the notes above. |
| `docs/guide/jira.md` [Jira-Change]                                     | Fires. Deferred to TCW-117.                                                                                           |
| `docs/guide/<topic>.md` [Guide-Topic-Change]                           | Fires (linking and validation, multi-repo store locations, the CLI output contract). Deferred to TCW-117.             |
| `docs/release-notes/upcoming/<folder>.md` [Public-API]                 | Written: `docs/release-notes/upcoming/TCW-110-tcw-4-0-full-identifiers-and-tcw-addresses.md`.                         |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change]               | Written: `docs/changelogs/upcoming/TCW-110-tcw-4-0-full-identifiers-and-tcw-addresses.md`.                            |
| `skills/<component>/SKILL.md` [Skill-Driven-Component]                 | Fires. Deferred to TCW-117.                                                                                           |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | Fires. Deferred to TCW-117.                                                                                           |
| `docs/use-cases.md` [Project-Setup-Change]                             | Fires (UC-4, UC-6). Deferred to TCW-117.                                                                              |

## Not done

- `pnpm test:e2e` and the QA plan's scenarios by hand are for qa, as the plan
  says; neither was run in this round.
- `tcw work advance TCW-110 --dry-run` (the records gate) is the dispatching
  session's to run.

## The web client

`pnpm exec tsc --noEmit`, `pnpm test` (15 files, 187 tests), `pnpm lint` and
`pnpm check:build` pass at `89e6bd44`, and `pnpm exec prettier --check` passes
over every file this item changed or created outside `tcw/serve/dist`.

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, run in full in the foreground as
CI runs it:

`5737 passed, 114 skipped in 553.56s`, at `89e6bd44` (2026-10-23).
