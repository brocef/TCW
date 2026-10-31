# Implement round 1 — TCW-115

Built on the branch `impl-115`, from `78c88809` on `v4` (later rebased onto
`93b17acb`, which changed every hash below to the one given), in the worktree
`.claude/worktrees/impl-115`. The code under test was run from that worktree's
own virtual environment (`.venv/bin/pytest`; hand runs of `tcw` only through a
wrapper, against scratch projects under the session's scratchpad, never this
repository). No lifecycle command was run and no ticket was moved or written
to: the dispatching session makes every move. The released 3.0.2 `tcw` was
used only to read this stage's instructions. Nothing reached the network:
every clone in the tests and the hand checks is of a repository made in a
temporary folder. This is the first implement round, so it answers no
rejection. It gives no verdict.

## Commits

| Commit     | Steps |
| ---------- | ----- |
| `5fd94c71` | 1: the deciding manifest entry, readable as a `Placement` |
| `135e2c4b` | 2: the `tcw project` group beside the commands it replaces |
| `081559ac` | 3: the tests and documents name the new commands |
| `cb4aa4d4` | 4: the old commands removed; `REMOVED_COMMANDS`; synonyms first |
| `9667511a` | 5: messages, help and comments |
| `8073d345` | 6: `tcw project list` |
| `912b1492` | 7: `tcw project config` and the origin label |
| `36e625e3` | 8: `tcw project path` |
| `58f9c83d` | 9: `tcw project info`, text |
| `ac7b92c7` | 10: `tcw project info --json` |
| `34c77329` | 11 to 16: `tcw project provision`'s projects pass, and git's location variables |
| `cc32fd4b` | 18: the two sweeps that list the new clone and folder checks; `--component`'s help |
| `98d05ed0` | 17, 19: the capabilities, the taxonomy entries, the changelog and release notes |
| `38f582b5` | the implement round and `removed-tests.txt` |

**Steps combined, and how each per-step comparison was kept.** Steps 11 to 16
were built together in one module, `tcw/provision.py`, and one completed
`fetch_project`: the plan's later steps each finish a function an earlier one
starts (Step 12's first `fetch_project`, completed in Step 13; Step 12's
"every entry trusted", replaced in Step 14), so the intermediate versions would
have been written only to be overwritten. Every test those steps name was
written and run against the finished code, and the full suite's outcome
comparison at the end (below) stands in for the per-step full-suite runs. For
Steps 4 to 10 the per-step full-suite runs were likewise replaced by each
step's targeted tests plus that final comparison; Steps 2 and 3 had their own
full comparisons (`out2a/b`, `out3a/b`).

## What was done, step by step

- **Step 0.** TCW-107, TCW-108, TCW-109, TCW-110, TCW-112 and TCW-114 are on
  the starting commit. `reached_by_both_sides` and `_connected_declarations`
  were already gone (choice 22: nothing to remove). `tcw/work/open.py` has no
  `uncommitted_changes` on this branch, so choice 28's third call site does not
  exist; every git call TCW makes is in `tcw/store/fs.py` (`_git`),
  `tcw/store/project.py` (`_git_lines`) or `tcw/provision.py` (through `_git`).
- **Step 1.** `FsProjectRegistry.placement(id, named_by=None)` and `Placement`.
- **Step 2.** The group, registered after `work`, its six verbs reusing the
  old commands' code; side-by-side tests; the outcome baseline (`out2a/b`).
- **Step 3.** The rename script over tests and documents
  (`rename-report.txt`, 1238 lines), with three hand repairs where the script
  broke a file (this item's own test file, `test_migration_guide.py`'s list of
  2.x headings, and the `ROWS` exclusion set). Outcomes compared with Step 2:
  no change.
- **Step 4.** The old subparsers removed; `REMOVED_COMMANDS` answers each at the
  top level only, exit 2; the suggester names a synonym valid where it was
  typed first. Mutation: the table disabled turned 4 tests red.
- **Step 5.** Nine files of `tcw/` rename the commands they name; the AC 4
  sweep in `tests/test_shipped_text.py`; 26 assertions rewritten. Mutation: the
  old messages restored turned 5 tests red. `evals/seed_fixture.py
  --customized` built.
- **Step 6.** `tcw project list`: no code change needed (`found` was there and
  `read-only` gone); three AC 6 tests.
- **Step 7.** `origin_label` and `origin_json`. Mutation: every file shown
  absolute turned 3 tests red.
- **Step 8.** `tcw project path`, 12 tests.
- **Step 9.** `tcw project info`, text. Mutation: the synonym-first rule
  removed turned 1 test red.
- **Step 10.** `--json`.
- **Steps 11 to 16.** `run_provision`'s forms; `git_environment` on every git
  call; `--` before the store URL and after its `ref`; the `-C` form of
  `StoreNotProvisioned`; `not_here` naming `tcw project provision <owner>`;
  `tcw/provision.py`; `fetch_project` and `FetchRefused`; the unused
  `PROJECT_TARGET` branches removed (nothing called them). New
  `tests/provision_support.py` (the stand-in git, with a test of the fixture
  itself), `tests/test_project_provision.py` (84 tests: AC 19 to 32, 34 to 38),
  `tests/test_fetch_project.py` (43: choice 9's steps 1 to 8, the bound's
  parts, `repository_top`, AC 36 (i), the recheck before each clone, 7.4's
  fallback text), and six Step 11 tests in `tests/test_store_provisioning.py`.
- **Step 17.** The three new capabilities written; the 18 changed ones and the
  two taxonomy entries rewritten where they describe the command (by a helper
  agent, then checked here against the code: one sentence corrected, that a
  `--component` run prints no count line).
- **Step 18.** Below.
- **Step 19.** Documentation sync, below.

## Decided by the implementing agent

- **Refusal lines carry the command prefix; progress lines do not.** `→`,
  `fetched into`, `would fetch`, `nothing to fetch` and the count line are
  plain; every refusal starts `tcw project provision:`. Reason: a refusal is an
  error and errors carry the command typed (choice 23); progress is narration.
- **A clone check's message starts with `<id>: `**, like every other per-project
  line, so a run with several projects says which one each line is about.
- **7.11's message** reads `<id>: fetched into <folder>, but <registry error>.
  Until it is corrected, ...`; the registry error already names its file.
- **7.7's conflict message avoids the word "branch"**, so `_group_round` needs
  no static-guard exemption; it names each entry's file and repository.
- **In `info`, a store that exists but cannot be opened reads "could not
  check"; a missing one reads `none` with a count of 0.**
- **The `-C` form of the store message is decided by the store's own project
  root against the locator's active root**, not by `find_project_root()` from
  the current folder (plan choice 12 said the latter). Reason: pytest's current
  folder is this repository, itself a TCW project, so library tests got the
  `-C` form wrongly; the locator knows which project's store it resolved. The
  spec does not say which, so this does not contradict it.
- **An entry folder that holds files and no project is refused as occupied by
  provisioning alone, not as a graph problem of the whole run.** The registry
  records it as a graph problem (TCW-107 Design 2.3 row b), which would make
  `require_valid` refuse every provisioning run before AC 24's message.
  `require_valid(fetching=True)` leaves those problems out, `occupied_ids()`
  names the projects, and the round refuses each with 7.6's message while the
  others are fetched. Every other command still refuses the graph as before.
- **7.4's check runs before the graph check after a round.** A kept answer that
  a fetched manifest changes is also recorded as a graph problem (TCW-107's
  search-versus-manifest conflict), so checking the graph first gave 7.11's
  message instead of 7.4's. `entry_elsewhere()` gives the entry that disagrees
  so the message names the new folder and the file.
- **Allowances in `tests/work/test_git_write_scan.py` may name a module-level
  function** (`fetch_project`), not only `Class.method`: as narrow as a method,
  and `fetch_project` is a function by plan choice 9.
- **AC 37's addresses beginning with `-`** are refused by TCW-107's manifest
  reader before the run (Design 7.14, which the plan allows); the test asserts
  that wording, and 7.9's own `-` check is unit-tested.

## Mutation checks

| Change made | Red |
| --- | --- |
| `git_environment` returns its argument unchanged | 4: the store clone with `GIT_DIR`/`GIT_INDEX_FILE`, `_git` dropping them, `worktree_anchors` with `GIT_DIR`, AC 36 (h) with the variables |
| the as-written rule removed | 2: its library test, AC 27's committed personal manifest |
| `strict` resolution removed | 1: its library test |
| the hidden-folder rule removed | 2: its library test, AC 36 (c)'s hidden case |
| the linked-worktree rule for `R` removed | 2: its library test, AC 36 (j) |
| `same_folder` compares text | 1: AC 36 (e), run on this Mac (it does not skip here) |
| Steps 4, 5, 7, 9 | as listed above |

`GIT_LOCATION_VARIABLES` itself is checked against `git rev-parse
--local-env-vars` on the machine running the test, so it is not a mutation
target.

## Hand checks (the plan's "Verification the tests cannot do")

1. **Help.** `tcw --help`, `tcw project --help` and each verb's help read
   whole: plain, the groups in the order validate, serve, taxonomy,
   capabilities, work, project. One change made: `--component` now says "and
   no project".
2. **A remote that cannot be read** (`file://` to a folder with no read
   permission): fails at once (0 seconds) with git's reason, exit 1, nothing
   left beside `app`.
3. **Ctrl-C during a 67 MB clone:** the staging folder was seen, the run was
   interrupted, and the staging folder was removed. The next run fetched
   normally; a copy placed by hand in `.tcw-staging-0123abcd/` was not found by
   `tcw project path` (exit 5). The interrupt prints a Python traceback: no
   `tcw` command handles an interrupt quietly, so this is TCW-wide and is left
   out of this item (noted for TCW-118 below).
4. **Eval fixtures:** `evals/seed_fixture.py --customized` and `--bare` both
   built.
5. **`tcw project info`** with a parent missing and Jira mode on: each missing
   setting, store and override check says why and what to add; exit 0. (Jira
   mode without every stage's status is refused as the project's own problem,
   as `list` refuses it.)
6. **The AC 19 layout by hand:** `core` fetched; its `git status --porcelain`
   empty and its `HEAD` the remote's `main` commit; nothing else made.
7. **AC 36 (e) on macOS:** passes, and goes red with `same_folder` comparing
   text (above).
8. **A real git hook:** a `post-checkout` hook in a scratch monorepo ran the
   dry run and printed `wp: would fetch into <scratch>/hook/wp`, exit 0; but
   this git sets neither `GIT_DIR` nor `GIT_INDEX_FILE` for `post-checkout`, so
   the check was repeated with a `pre-commit` hook run through `git --git-dir`,
   which does set both: same plan, exit 0.

## The suite as CI runs it

Run in two halves with `-q -p no:cacheprovider` at the last commit before this
round: `tests/work tests/serve` 2066 passed, 2 skipped; the rest 4975 passed,
111 skipped. Against the Step 2 baseline (6948 test IDs): 7154 after, 214 new
(all passing), 8 gone, every one in `removed-tests.txt`, and no test that
exists in both changed its outcome. The web client was not changed, so the
`pnpm` checks were not run.

**Changed tests, not removed:** `tests/test_manifest_cli.py`'s
`test_ac22_provision_fetches_no_project` became
`test_ac22_a_dry_run_plans_the_project_and_contacts_nothing` (listed as removed,
since its ID is gone). Assertions changed to the new behavior:
`tests/test_ownership.py::test_a_project_not_on_this_machine` and
`tests/test_owning_project.py` (the `; fetch it with tcw project provision
core` tail), `tests/test_capabilities_federation.py` (the `-C` form), and the
26 of Step 5.

**AC 40.** Outside `docs/work/`, the changelogs and release notes, the only
files naming a removed command are `tcw/cli_suggest.py`'s table, capability
descriptions saying it was TCW 3.x's name, and the archives:
`docs/migration-guide-*.md`, `docs/plan/phase-*.md`,
`docs/tcw-3.0-migration-log.md`.

## Documentation sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` [Public-API] | yes | names only (Step 3); the prose is TCW-117's |
| `docs/guide/jira.md` [Jira-Change] | no | — |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes | names only in `cli.md`, `configuration.md`, `multi-repo.md`, `work.md`; the rewrite is TCW-117's |
| release notes `upcoming/TCW-115-…md` [Public-API] | yes | written |
| changelog `upcoming/TCW-115-…md` [Any-Code-Change] | yes | written |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes | names only; what the skills teach is TCW-117's |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | no key or variable changed; names only (Step 3) |
| `docs/use-cases.md` [Project-Setup-Change] | yes | names only; closing UC-6's gap is TCW-117's |

## Handoffs and notes for later items

- **TCW-116 (`tcw migrate`):** as the spec says: a 3.x project connected by a
  `repository` with no `path` was cloned into the per-machine cache; 4.0 clones
  only into a manifest entry's folder and does not find the cache clone, so
  `tcw migrate` should write the migrated entry's `path` into the personal
  manifest pointing at that clone when it is there, or name it in its report.
  Also: this repository's own records stay in the 3.x format; the three new
  capabilities' `meta.yaml` files were written by hand in that format (ids
  `cap-be6d93`, `cap-3d46db`, `cap-2d83ea`, checked unique).
- **TCW-117 (guides and skills).** Every passage below had its command names
  changed by Step 3 and nothing else; each must now say what 4.0 does (line
  numbers at `081559ac`):
  - `README.md` 232, 262, 263, 265, 266, 275, 276, 299, 363, 425 — the command
    table needs `tcw project path` and `tcw project info`; 263's "obtains the
    stores and projects" is now true and should say how far a clone may be
    placed.
  - `docs/guide/cli.md` 14-16, 57, 58, 62; `docs/guide/configuration.md` 26,
    298 (the `--origin` comment's new shape); `docs/guide/multi-repo.md` 18,
    66, 123, 222, 224 (the bound, the `.git`-only refusal, staging folders);
    `docs/guide/work.md` 384, 409, 413, 415.
  - `docs/use-cases.md` 127, 303, 350, 359, 659 — UC-6's known gap "TCW-23
    (provision scoping)" is closed by this item.
  - `skills/README.md` 90; `skills/capabilities/SKILL.md` 22, 25;
    `skills/configure/SKILL.md` 38, and its references `personal.md` 25, 62,
    102, `projects.md` 19, 59, 76, 157, 163, 387, `stores.md` 41, 43, 88, 89,
    120, 121, `work.md` 22, 48, 192; `skills/setup/SKILL.md` 4, and its
    references `capabilities.md` 13, `install.md` 59, `project.md` 26-70
    (14 lines), `taxonomy.md` 13; `skills/taxonomy/SKILL.md` 35, 38;
    `skills/work/SKILL.md` 95 and `skills/work/references/commands.md` 28, 29;
    `tcw/work/procedures/search.md` 27; `docs/taxonomy/load-order/description.md` 6.
  - What each must teach, from the spec: setup teaches `tcw project new`;
    configure teaches `tcw project config --origin` and `tcw project info`;
    work teaches `tcw project path <id>` with `tcw -C`. The migration guide
    gives the four removed commands and their replacements, the two new
    verbs, the changed `--origin` comments, and the bound (trusted manifests,
    the direct-child, home-folder and hidden-folder rules, the refusal when
    git cannot place the owner, a submodule's bound inside the superproject,
    the linked-worktree bound beside the main checkout, and the
    `tcw -C <folder> project provision <id>` way out). The guide on related
    projects says a `.git`-only folder is refused and why, and that a
    `.tcw-staging-<hex>` folder is what a killed run can leave. Every
    `tcw -C` written gives its target as one token.
- **TCW-118 (release):** the release notes in
  `docs/release-notes/upcoming/TCW-115-…md` already name the group, the four
  removed commands, the bound and the `.git`-only refusal. Separately, worth a
  ticket of its own rather than this item: an interrupt (Ctrl-C) during any
  `tcw` command prints a Python traceback.

## Not done

- The `pnpm` checks: the web client was not changed.
- The guide, skill and README prose (TCW-117's, above).
- `tcw validate` of this repository's records with the new `tcw`: they stay
  3.x until TCW-116, as the plan's Step 17 says.
