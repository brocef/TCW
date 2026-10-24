# Implement round 1 — TCW-112

Built on the branch `impl-112`, in the worktree `.claude/worktrees/impl-112`,
with the code under test run from that worktree's own virtual environment
(`.venv/bin/pytest`, `.venv/bin/tcw`). No lifecycle command was run from this
worktree, no ticket was moved and nothing was posted: the dispatching session
makes every move. Hand checks ran in scratch projects with `HOME` and the XDG
folders pointed at the scratchpad and every `TCW_*` variable unset; the
repository itself was never used as a project. This is the first implement
round, so it answers no rejection. It gives no verdict.

Commits: `4a04c94c` (Steps 1 and 2), `983235ed` (everything else), `ab76d5ce`
(one skill line found by the documentation pass), and this round.

## How the work departed from the plan

**The interim steps were collapsed into one rewrite** (decided by the
implementing agent). The plan builds the view in stages — Step 3 on top of
the old federation walk, Step 5b and 5c removing `extends` around it, Steps 7
and 8 replacing `get_inherited` and the pointer — with interim `xfail` marks
and an outcome comparison at each step. Once Steps 1 and 2 had landed, the
old walk, the pointer index and the `extends` methods were so interlocked
that keeping each interim state green would have meant writing, and then
deleting, three adapters between them. The store classes were instead
rewritten once against the finished design, and every test was converted to
it. The plan's commit boundaries were therefore two commits rather than one
per step; each is green. What each step asked for is still done and is
listed below by step, and the mutation checks the plan asks for were run
against the finished code.

## What was done, step by step

- **Step 0.** TCW-106 to TCW-111 are on the branch. Baseline before any
  change: 1985 passed, 2 skipped (`tests/work tests/serve`); 4358 passed,
  111 skipped (the rest). TCW-109's `known_keys()` is used only to place
  `work.tags` and `work.jira` problems and to decide undecided keys
  (`tcw/config.py:1117`, `:1263`): it never reports a key a file holds, so
  `extends` in another project's file does not make it unreadable, and Step
  5c needs no reordering. No `tcw project` group exists (`tcw/cli.py`
  registers `projects`), so Step 18 builds nothing (below).
- **Steps 1 and 2** (`4a04c94c`). `combine`, `Declaration`, `Combined`,
  `Unused`, `missing_parts`, `clash_warning` in `tcw/store/base.py`;
  `InheritedUnavailable`'s `"store"` reason and `detail`, and
  `unavailable(..., store_message=)`. `tests/test_combine.py`, 40 tests,
  including the property test (`random.Random(112)`).
- **Steps 3, 5b, 5c — inheritance from the parent links; `extends` gone.**
  `FsTreeStore` reads its sources with `registry.source_entries`, opens each
  source's store through the command's `Locator` (`Locator.store`), and
  builds one `_View` on demand. A project whose own file names no parent
  asks the registry nothing (UC-1, AC 35). `extends` in the active project's
  own file is a `StoreDeclarationError` with Design 1.5's message (exit 1,
  an error in `tcw validate`); in another project's file it is not read.
  The `extends` commands, the store methods, `_FederationWalk`,
  `_FederationCycles`, `_extended_component_stores`, `_persist_extends`,
  `_extends_label`, and the two `known_keys()` rows are removed.
- **Steps 4, 6, 9, 10, 11 — the conversions.** About 50 test files moved
  off `extends`, the `overrides:` pointer and `id: cap-…`. The shared
  fixtures `tests/inherit.py` and `tests/test_capabilities_rm.py`
  (`federated`, and `write_cap(..., complete=False)` for a 4.0 override)
  were converted first. Tests of a removed feature were deleted or
  rewritten to its replacement: in `test_taxonomy.py` (68 → 60 functions),
  `test_capabilities_federation.py` (50 → 43), `test_config_edit_writers.py`
  (33 → 24, the `extends` writers), `test_store_provisioning.py` (95 → 93),
  `test_cli_contract.py`, `test_taxonomy_cli_contract.py` and
  `test_override_references.py` (one each). Tests whose 4.0 outcome changed
  on purpose: `test_refs.py` (an address asks existence only, so an
  unparsable state file is found; a new test that a project missing above
  the owner does not stop it), `test_inherited_config.py` (a missing parent
  in the configuration-gap tests passes only `config`, so the test keeps its
  subject), `serve/test_work_read.py` (an `InheritedUnavailable` is now 503),
  `test_findings_type.py` and `test_validate_command.py` (field findings at
  the state file, below).
- **Steps 7, 8 — reading and writing by path.** `get_view`, `get_local`
  (combined; only the project's own object), `declaration` (marked
  partial), `chain`, `inherited_at`, `view_warnings`, `own_paths`,
  `has_own`; `override_target` and `removal_target` (choice 9);
  `find_tree_writable(store, text, *, removing)`. `set` writes the project's
  own state file at the id-path holding only the fields given; `reset`
  takes the id-path, the project's own full identifier or the overridden
  object's; `rm` removes an override and prints `<id-path> now shows <full
  id>`; `tcw capabilities add` at an inherited path is refused (Design
  4.1); `tcw taxonomy add` there writes an override of what differs and
  prints `<new> overrides <inherited>`. `Capability.id`, `get_by_id`,
  `_mint_cap_id`, `_apply_override`, the override index and `AmbiguousRef`
  are removed.
- **Step 12 — two unrelated projects at one path.** The later one in load
  order, whole, with Design 2.5's warning in `list`, `search` and `tcw
  validate`, until a complete object of the project's own decides it.
- **Step 13 — inherited content only when needed.** `list --local`, `show`
  of an own object, `set` and `rm` of an own object work with a parent
  missing (records `"partial": true`, `own_only` warning); everything that
  needs the view exits 7. `Locator.exists` answers existence from the
  owner's own store alone; `resolve_address` and the records gate's term
  check use it.
- **Step 14 — a source's object with a version problem** (AC 39): left out
  of listings with exit 1; `show` and `reset` raise it; `set` of the own
  override stands; `tcw validate` gives one `could not check` finding.
- **Step 15 — each own object checked as the project sees it.** Fields on
  the combined object, references on what the project declares; Design
  6.1, 6.4, 6.5; row k for capabilities; a scoped check reads only its own
  object, so a malformed sibling never stops it.
- **Step 16 — the records gate and drift.** Every entry routes to its
  owner's own ledger; `capability` reads the owner's combined `Status`;
  `removal` asks `has_own`; `INHERITED` is gone; `InheritedUnavailable` is
  unchecked. Drift builds the view first; an override that sets no
  `Status` is never ruled on.
- **Steps 17a, 17b — the web app.** `overrides`/`partial` in records; 503
  `inherited-unavailable`; writes allowed only when the served project
  owns the object (403 `read-only` otherwise, keeping the backticked
  `tcw capabilities set` hint); `declaredDescription` in every capability
  answer; the editor's body field starts from it, with a note when the
  page's body holds more; the entry view shows "overrides `<full id>`" or
  the partial line. `tests/serve/test_overrides.py` (17 tests) and four
  client tests.
- **Step 18.** `tcw project info` does not exist; nothing built (note to
  TCW-115 below).
- **Steps 5a, 19, 21 — shipped text and this repository's records.**
  `README.md`, `docs/guide/` (`cli.md`, `linking-and-validation.md`,
  `multi-repo.md`, `taxonomy-and-capabilities.md`), `skills/taxonomy`,
  `skills/capabilities`, `skills/configure` (`SKILL.md`, `projects.md`,
  `stores.md`, `personal.md`), `skills/setup/references/taxonomy.md`;
  the capabilities the spec lists, and the new
  `taxonomy/override-an-inherited-term` and `docs/taxonomy/override/`, in
  3.x form (`meta.yaml`, `id: cap-…`), edited by hand.
- **Step 20.** `tests/test_no_3x_inheritance.py`: no removed message or
  function in `tcw/`; no test file writes the three 3.x fixture forms
  except the files named with the refusal each tests; an allowed entry no
  longer needed fails too. `MIGRATION_CODE = ()` and `MIGRATION_TESTS = ()`
  for TCW-116.
- **Step 23.** The two upcoming entries, named after the item folder,
  formatted with `prettier`; `tests/test_upcoming_entries.py` green.

## Decisions made by the implementing agent

Each is within the spec; none contradicts it.

1. The interim steps were collapsed (above).
2. `set --parent ''` writes `parent: null`, and `--field K=` (an empty
   value) writes `K: null`: Design 4.2's one rule that a cleared value is an
   explicit `null` on every own object, and plan Step 8's "the clear value".
3. `tcw taxonomy add --parent P` with an inherited `P` puts the new term
   inside `P`'s path only when that nested path is itself inherited (so it
   is an override there); otherwise it is placed as `add` places any term.
4. "missing Status" is dropped entirely, overrides included: an override
   inherits its `Status`, and an object overriding nothing is covered by
   6.1's message.
5. A taxonomy override that declares no `kind` still has its `vocabulary`
   read for the referrer check, since it may be a Feature by inheritance.
6. When an object a reference names cannot be read here, the reference
   check treats it as present and skips the kind check (no false "not a
   Feature").
7. Field-value findings (unknown or retired field, invalid value, Partial
   without Gaps, Blocked without Blocked by) are reported at the state
   file, not the folder: AC 16 asks for the unknown field "at `cli/y`'s
   state file", and one place for every field finding keeps them together.
8. `reset`'s refusal while references name the override:
   `cannot reset '<input>': <full id> is still named by <full id> (<field>),
   ...; repoint each at <inherited full id> first`, naming each referrer by
   its full identifier (Design 4.3).
9. `resolve_address`'s "other project" answer: an owner the active project
   does not inherit the axis from; existence alone decides `ok`.
10. A record read from another owner's store says `origin` from the asking
    store's side (`_as_seen_here`), so `origin` is "local" only for the
    active project's own objects.
11. A source whose store fails to open for any reason (not only
    `StoreNotProvisioned` or `StoreDeclarationError`) is Design 1.3's third
    case, exit 7 with the store's message.
12. `tests/test_tree_store_raises.py` allows `StoreDeclarationError`,
    `InheritedUnavailable`, and the names `unavailable`, `view_error` and
    `unreadable_problem` that raise it or a `StateFileProblem`.

## Mutation checks

Each turned the named tests red, and each was put back:

- `passes` read as "earlier in the load order": 16 of `test_combine.py`
  red, AC 11 and the property test among them (Step 1).
- No parent links read: 13 of `test_tree_inheritance.py` red.
- Design 6.1 never reported: 2 of `test_overrides_by_path.py` red.
- `extends` not refused: 4 of `test_no_extends.py` red; refused in a
  parent's file too: 2 red across `test_no_extends.py` and
  `test_capabilities_federation.py`.
- No partial fallback for an own object: 4 of `test_tree_parent_missing.py`.
- The gate reading the view instead of the owner's own object, and
  `removal` counting an inherited object: AC 31's removal test red each time.
- `declaredDescription` answered with the combined body: 3 of
  `serve/test_overrides.py`; the editor starting from the combined body: 2
  client tests.
- The guard: a removed name and message appended to `tcw/refs.py` turned
  both code rules red; each fixture form in a scratch folder is reported
  (kept as a test).

## Suite

At `ab76d5ce`, run as CI runs it, in two halves with `-q -p no:cacheprovider`:

- `tests/work tests/serve`: 2004 passed, 2 skipped.
- the rest: 4549 passed, 111 skipped.

Web client: `pnpm test` 196 passed; `pnpm exec tsc --noEmit` clean;
`pnpm lint` clean; `pnpm build` and `pnpm check:build` pass. `prettier
--check .` reports files this item did not touch (recorded Jira fixtures
under `tests/work/jira/recorded/`); every web file this item changed passes.

## Documentation entries

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes | The `extends` lines changed; the fuller rewrite is TCW-117's. |
| `docs/guide/jira.md` | no | Nothing about tickets changed. |
| `docs/guide/<topic>.md` | yes | `taxonomy-and-capabilities.md`, `multi-repo.md`, `linking-and-validation.md`, `cli.md`: removed commands and keys, and the override rules. |
| release notes, changelog | yes | Written. |
| `skills/<component>/SKILL.md` | yes | `taxonomy` and `capabilities`: inheritance from parents, overrides by path, `add` at an inherited path, `reset` by full identifier, `rm` of an override, `partial` records, exit 7, clearing a field. |
| `skills/configure/references/` | yes | `projects.md`, `stores.md`, `personal.md`. |
| `docs/use-cases.md` | yes | Deferred to TCW-117 (below). |

## Notes for the later items

- **TCW-113:** the view is `get_view` and `list_all()`; `--scope own` is
  `list_all(local_only=True)` (or `own_declarations()` without the view);
  `--project <id>` reads `get_local` of that project's store; the web app
  answers `InheritedUnavailable` with 503; its write rule is "owner is the
  served project"; capability answers carry `declaredDescription`;
  existence without the view is `Locator.exists`.
- **TCW-114:** Design 2.7 is `inherited_at(id_path)`; the chain is
  `chain(id_path)`; the refusals its Design 1.3 rewords live only in
  `override_target` (Design 4.2's message) and `removal_target` (Design
  4.4's); `find_tree_writable(..., removing=)` has no default and always
  returns the active project's own full identifier, so a `check_owned`
  placed after it always passes. Both methods refuse a project outside the
  sources before reading anything. The web app's `_owned`
  (`tcw/serve/records.py`) is the third refusal site.
- **TCW-115:** `tcw project info` does not exist on this branch; Design
  3.7's inputs are the `list --local --json` records (their `overrides`)
  and `view_warnings()`.
- **TCW-116:** a 3.x override moves to the id-path of what its pointer
  resolves to, often not its folder's name; a move onto an occupied path is
  reported, not made; `id: cap-…` must go (row k); a hand-written object
  overriding nothing needs `name`, `Status` and `description.md` (6.1); an
  override that lists no `prependedDocs`/`appendedDocs` while its original
  does changes its body; this repository's records are in 3.x form; fill
  `MIGRATION_CODE`/`MIGRATION_TESTS` in `tests/test_no_3x_inheritance.py`.
- **TCW-117:** `docs/use-cases.md` (UC-2, UC-3, UC-6, S-4, S-6; lines 92,
  142-189, 369, 509) says nothing yet of inheritance from parents; the
  guides and skills were changed only enough to name no removed command
  and state no removed rule — `docs/guide/taxonomy-and-capabilities.md` and
  `skills/capabilities/SKILL.md` still say `meta.yaml` in places; the
  design's "Listings mark each object that replaces an inherited one" line
  needs amending (records carry `overrides`, the plain listing no mark).

## Not done

- Nothing in the plan is left undone. The helpers that converted tests and
  wrote the new test files did not deliver their own written reports; their
  work was checked by the suite and the mutation checks above instead.

## Added by the dispatching session

- `cli/read-from-an-upstream-project` is taken out of this item's
  `capabilities.yaml` `changed:` list, decided by the dispatching session on
  2026-10-24: TCW-108 removed that capability (its ledger lists it under
  `removed:`), so the records gate refused the move to review with "declared
  changed but not in the ledger". The spec (line 118) and plan named it
  before TCW-108 had landed.
