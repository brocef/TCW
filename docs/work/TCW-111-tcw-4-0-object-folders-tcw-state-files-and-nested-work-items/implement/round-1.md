# Implement round 1 — TCW-111

Built on the branch `impl-111`, made from `v4` at `87729a98`, in the worktree
`.claude/worktrees/impl-111`, with the code under test run from that
worktree's own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). No
lifecycle command was run from this worktree: the dispatching session makes
every move. The records of Step 18 were written in their 3.x form and checked
with the released 3.x CLI on a copy, as described there. This is the first
implement round, so it answers no rejection. It gives no verdict.

The full suite was run at the end of each part of the plan (after Steps 5,
7, 8, 11, 16 and 14) and at the end, rather than after every step; each step
ran the tests it names and the files around them. That is the one change to
how the plan said to work.

## What was done, step by step

- **Step 0 — the starting point.** TCW-106, TCW-107, TCW-108 and TCW-110
  are on `v4`. One correction to the plan: TCW-108's `connect_projects`
  takes the relation `"parent"`, not `"parents"`; the plan's two citations
  were corrected. The baseline at `87729a98`: 1912 passed and 2 skipped in
  `tests/work tests/serve`; 3987 passed and 111 skipped in the rest.
- **Step 1 — one module for object folders** (`8f7c67e5`).
  `tcw/object_folders.py`: the state file names and their 3.x names, the
  reserved names per store, `walk` and its classes, `object_paths`,
  `is_object`, `objects_below`, `folder_parent`, `removal_blockers`,
  `shape_problems` (rows a to h), `read_state`, `state_text`, `disagreement`.
- **Steps 3, 4 and 5 — state files** (`703166fd`, `2ef73295`, `5275c6e8`).
  `tests/statefiles.py` and `tests/objectcli.py`; the inventory of every
  test and its assertion count, kept in the scratchpad; `meta.yaml` and
  `item.yaml` replaced by `tcw-taxonomy.yaml`, `tcw-capability.yaml` and
  `tcw-work-item.yaml`, each written with its version line first, an existing
  one kept on edit; a version problem means the object is never read
  (`StateFileProblem`, or the backend's `Unreadable`), and list and search
  name it on standard error and exit 1 (`tcw/output.py` `left_out`); row k
  (an `id` must equal its folder's name). 56 test files were converted by a
  script, then fixed by hand. Kept at their 3.x names on purpose:
  `tests/test_ledger_3_0.py`, `tests/test_documented_cli_surface.py:306`,
  `tests/test_migration_guide.py`, and `tests/test_git_example.py` until
  Step 16.
- **Step 6 — the tree stores list by the walk** (`4004b5f9`). A folder with
  no state file is never a term; reserved names are refused by `add`; the
  removal checks use `removal_blockers`, and a 3.x file below names
  `tcw migrate`.
- **Step 7 — a term's or capability's folder is bounded** (`71ffcc02`).
  Attachments and composed documents come from `resources/` only; rows a to
  g for the tree stores; `tcw validate` skips YAML under `resources/`.
- **Step 8 — both work backends find items by id-path** (`12d8181b`).
  `read_all`, `Layout.item_folders`, `work_store_problems` and
  `jira_store_problems` use the walk; the Jira lookup has a walk cache and a
  key index; a key-named folder needs its state file; adopt and
  `tickets list` find a key's folder at any depth; the web app reads a nested
  item by its percent-encoded id-path.
- **Step 17 — the sweep guard** (`8b6b9e2a`), moved to the end of Part 2 as
  the plan orders. `tests/test_object_folder_sweep.py`, with `offenders(root)`
  one function of a root folder and `MIGRATION_FOLDERS = ()`.
- **Step 2 — the 255-character limit** (`ced3c133`). `ID_LIMIT`,
  `length_problem`; the parsers refuse longer input; `words_room`,
  `fitted_words` (with Step 11's `refuse` written at once).
- **Step 9 — `tcw work new --nest`** (`24e5ac21`). `create(..., nest=)` in
  every backend, `nesting_parent`, the interface's parameters renamed
  `id_path`.
- **Step 10 — the web app's create** (`febac881`). `nest` on `POST
/api/work`; the form's "Put its folder inside the parent's folder",
  unticked by default and disabled until a parent is given; `pnpm build`.
- **Step 11 — no full identifier over 255 characters** (`a5cdabb2`). Tree
  `add`, files `create`, Jira `create` (refused before the ticket, cut to the
  key's room after), fresh adoption, delegation; row n.
- **Step 12 — rename by id-path** (`4378666a`). Both backends rename within
  the holding folder, check the limit, and refuse an item with items nested
  in it (`refuse_nested_rename`). `SLUG_HELP` says id-path for every item
  argument.
- **Step 15 — shipped text** (`90bdd5b7`). The plan stage prompt's step 6,
  `docs/lifecycle/abstraction.md` as Design 9.1 writes it, "Twelve
  operations".
- **Step 16 — the commit hook** (`7908f853`). Leaves items nested in the
  moved one out of its staging and commit; the configuration guide shows the
  new script byte for byte, as its test requires, with one sentence added.
- **Steps 13 and 14 — `parent` and the disagreement warning** (`6651a813`),
  one commit, since both are in the same functions. `parent` on `Term` and
  `Capability`; `taxonomy add --parent`, `capabilities add|set --parent`;
  rows l and m for the tree stores; row m for work items (files offline,
  Jira under `--remote`), and on `tcw work edit --parent`.
- **Step 18 — this repository's records** (`d63e5744`).
- **Step 20 — the upcoming entries** (`756e7fd5`).
- **Step 21 — the suite as CI runs it**, below; a case-insensitive disk test
  (`87ca0ea3`) and the formatting of one changed file (`10b05fbf`).

## Decisions made by the implementing agent

Each settles a question the spec and plan left open; none contradicts the
spec.

1. **The walk.** A 3.x folder (row f) and a folder named as an item with no
   state file (row h) are traversed like object folders: their fixed folders
   are entered but not reported as reserved, and loose files in them are not
   reported; they count as objects for row e. Below a misplaced or reserved
   folder, nothing is reported again. Reason: one finding per mistake.
2. **A state file that does not parse stays listable**; only a readable
   version problem leaves an object out of listings. Reason: the parse error
   is reported by the full check, and the version rule is about versions.
3. **Hidden files under `resources/` are not attachments**, as 3.x left out
   dot files.
4. **A listed document when `resources/` does not exist yet** is "missing
   attachment", decided by its spelling, not "not in resources/".
5. **A check of one object** (how `tcw serve` checks what it wrote) keeps
   rows a, b, c and f for what sits directly in that object's folder, row n
   for the object itself, and nothing for an inherited object; its parent
   check reads only the objects up the selected one's chain, never the whole
   store, which may hold a broken file.
6. **Messages:** the reserved-name refusal, "invalid slug 'resources':
   'resources' is reserved in the taxonomy store", follows row c; row h in
   files mode, "is missing; it holds the item's properties and stage",
   follows Jira's; `--nest` without `--parent`, "--nest puts the item's
   folder inside its parent's; give the parent with --parent"; the note for
   another project's parent, "not nested: <P> belongs to project '<id>', so
   the item's folder is made at the top of this project's work folder"; a
   Jira key leaving no room, "created Jira ticket <KEY>, but the key leaves
   no room for title words under <parent>, since no full identifier is
   longer than 255; finish with `tcw work tickets adopt <KEY>`"; a loop,
   "parent forms a loop: a -> b -> a", reported at each member, and an
   object naming itself said once, as "parent names the object itself".
7. **`tickets list`** leaves out a key that has any folder, made or not, so
   every key it lists can be adopted.
8. **The plan stage prompt** is at its 60-line limit, so step 6 was
   rewritten within its ten lines and "this item is the parent" was dropped;
   `--parent <slug>` says it. The recorded bytes in
   `tests/fixtures/prompt_fallback/unconfigured.json` were replaced for that
   step only, text for text, and the test's docstring says so.
9. **Records keep `"schema": 2`**: `parent` is an added key.
10. **The web app's term create answers 400** for a parent that names
    nothing, not 404: it is a bad field in the request, as every other
    refused value is. The CLI exits 4, as choice 9 says.
11. **`SLUG_HELP`**, the help of every item argument, says id-path, not only
    `rename`'s, since every command now takes one.

## Deviations from the plan

- **The clock in the nested-date test.** `FsWorkBackend` takes `today` when
  it is built and the CLI offers no way to set it, so the tests use the real
  clock with parents dated 2000-01-01. The plan's case of a part silently
  taking a top-level parent's date cannot be seen: the returned item is read
  back from the last part. The case under an organising folder can, and was
  seen to fail before the fix (exit 1, "Invalid isoformat string:
  '2026/2000-'"; the CLI turns the error into a message, not a traceback).
- **Choice 3's test** was first written over `parents: [{id: core, inherit:
[capabilities]}]`, where the command is refused by `find_tree_writable`,
  not by the new code (its mutation survived). It was rebuilt on
  `tests.test_capabilities_rm.federated`, which inherits through `extends`.
- **The sweep allowlist** gained two entries the plan did not have:
  `tcw/store/project.py` `_list_folder` (the project registry's search for
  project folders) and `tcw/store/fs.py` `_resource_files` (one object's
  `resources/`). The walk's own listing is `_entries`, not `_visit`.

## Mutation checks

Each new test was seen to fail with the code it checks broken, then pass
with it restored:

| Step  | Broken                                                                         | Red               |
| ----- | ------------------------------------------------------------------------------ | ----------------- |
| 5     | state files read without the version check; written without the line           | 10 of 18; 5       |
| 5     | the test helper without the version line; constants back to 3.x                | 77; 64            |
| 6     | four walk rules reverted                                                       | 6                 |
| 7     | the `resources/` skip, the shape findings, the composed-body rule              | 8                 |
| 8     | `read_all` top-level only; `link_exists` back to "is a folder"                 | 2; 1              |
| 17    | a listing of the work path, `os.listdir` and `"meta.yaml"` added               | 3 named offenders |
| 9     | `nesting_parent` always None; the created date from the whole path             | 8; 1              |
| 10    | `nest` sent whenever a parent is set; ticked by default                        | 1; 1              |
| 11    | tree `add` check, row n, files words, Jira refusal, adopt refusal              | 2, 3, 5, 1, 1     |
| 12    | no refusal; moved to the top; date of the whole path                           | 2; 3; 1           |
| 16    | no exclusion; exclusion on staging only; `resources/` not skipped              | each red          |
| 13–14 | work row m, tree row m, tree parent ref, loop, inherited set, taxonomy at root | 3, 1, 4, 1, 1, 1  |

## Handoffs

- **TCW-108:** none outstanding; its `connect_projects` spelling is
  `"parent"`.
- **TCW-110:** `tcw/ids.py` had no length limit; this item added it
  (`ID_LIMIT`, `length_problem`).
- **TCW-112:** `tcw capabilities set --parent` refuses an inherited
  capability until overrides by path; the walk returns 3.x override folders,
  told apart by `overrides:` (`_is_override`), and they are left out of row
  n; `prependedDocs` and `appendedDocs` are read only from `resources/`.
- **TCW-114:** the release note and changelog do not mention that renaming
  an item with nested items is refused, since TCW-114 lifts it in the same
  release; if it does not land in 4.0, its own `upcoming/` entry must say so.
  `objects_below`, `nesting_parent` and `refuse_nested_rename` are the
  helpers its move and rename can reuse; `report_mentions` searches for the
  old id-path; a rename of a term or capability with nested objects meets
  the same question.
- **TCW-116:** `tests/test_ledger_3_0.py` reads this repository's
  `meta.yaml` files by name and changes when it is migrated; until a store is
  migrated, `rm` of a term or capability with a 3.x folder below it is
  refused naming `tcw migrate`; the commit hook leaves out folders holding
  `tcw-work-item.yaml`, so after migration a nested child here is committed
  with its own moves only; `tcw migrate` must report a hand-written `id:`
  that differs from the folder's name; `MIGRATION_FOLDERS` in the sweep guard
  is where `tcw migrate`'s folder goes.
- **TCW-117:** the documentation deferred below, and beyond the spec's list:
  the web create form's option; `tcw capabilities add|set --parent`; the new
  `tcw validate` messages of rows a to n; that a long design goes in an
  item's `resources/`; `tcw work new --nest` in `docs/guide/cli.md`.

## Documentation entries

| Entry                          | Answer                                                                                                                                                                                                                      |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`                    | Deferred to TCW-117: state files, `resources/`, `--nest`.                                                                                                                                                                   |
| `docs/guide/jira.md`           | Deferred to TCW-117: the item folder holds `tcw-work-item.yaml`; `TCW Item` holds a nested id-path; a key is found at any depth.                                                                                            |
| `docs/guide/<topic>.md`        | Deferred to TCW-117: which files TCW treats as its records, `resources/`, organising folders. `docs/guide/configuration.md` was changed here only because its test requires the hook script byte for byte.                  |
| `docs/release-notes/upcoming/` | Written.                                                                                                                                                                                                                    |
| `docs/changelogs/upcoming/`    | Written.                                                                                                                                                                                                                    |
| `skills/*/SKILL.md`            | Deferred to TCW-117 (Design 9.3): the `work` skill's "Epics are parents" bullet and its command reference always pass `--nest`; the `taxonomy` and `capabilities` skills name the state files, `resources/` and `--parent`. |
| `skills/configure/references/` | Does not fire: no configuration key changed.                                                                                                                                                                                |
| `docs/use-cases.md`            | Deferred to TCW-117: S-10's "item folder" becomes "object folder".                                                                                                                                                          |

## Verification beyond the suite

- **By hand**, in a scratch project made with `.venv/bin/tcw init`: an epic
  and a part made with `--nest`, both listed by id-path; renaming the epic
  refused (exit 3); `taxonomy add --parent` nesting; `capabilities add
--parent`; a stray file in a term's folder reported, a file in its
  `resources/` not. The Jira scenarios are for qa, against a test project.
- **A case-insensitive disk**: the `Resources/` test ran (not skipped) on
  this Mac's disk and passed.
- **The cost of the walk**: 300 items, `tcw work list --all` 0.25 s and
  `tcw validate` 0.39 s with this branch, against 0.32 s and 0.44 s with the
  released 3.0.2 over the same items in the 3.x layout.
- **The 3.x records of Step 18**, copied with the configuration to a scratch
  folder (the work section left out, so no tracker is read) and checked with
  the released `tcw validate`: 0 errors, 0 warnings.
- **Not done:** `pnpm test:e2e` (needs a browser), and the check that this
  repository's lifecycle still runs on `v4` with the lifecycle CLI, which is
  the dispatching session's (no lifecycle command is run from here).

## The suite, as CI runs it

Bare `.venv/bin/pytest` from the worktree's root, in two halves:

- `tests/work tests/serve`: 1982 passed, 2 skipped.
- the rest: 4125 passed, 111 skipped.

Against the baseline: 6107 passed in all, from 5899; no test was lost that
was not renamed, and no assertion count fell (the inventory, taken again
after Steps 5 and 8). The web client: `pnpm install --frozen-lockfile`,
`pnpm check:build` (passes), `pnpm test` (191 passed), `pnpm exec tsc
--noEmit` and `pnpm lint` (clean). `prettier --check` over every changed
file passes except `tcw/work/prompts/plan.md` and
`tests/fixtures/prompt_fallback/unconfigured.json`, which were not formatted
before this item either; formatting the prompt would change bytes its
fallback test records.
