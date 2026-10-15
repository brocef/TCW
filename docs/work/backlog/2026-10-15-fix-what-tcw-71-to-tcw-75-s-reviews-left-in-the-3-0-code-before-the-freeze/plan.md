# Plan — Fix what TCW-71 to TCW-75's reviews left in the 3.0 code, before the freeze

This plan follows `spec.md`. Finding numbers (J1, P4, …) and criterion numbers
are the spec's. Every file and line named was read on `epic/tcw-3.0` at
`e301bef5`; re-read each before changing it, since the branch may have moved.

## Rules for this item (the owner's, for the TCW 3.0 epic)

- **Where the work happens.** A worktree
  `.worktrees/2026-10-15-fix-what-tcw-71-to-tcw-75-s-reviews-left-in-the-3-0-code-before-the-freeze`
  on branch
  `work/2026-10-15-fix-what-tcw-71-to-tcw-75-s-reviews-left-in-the-3-0-code-before-the-freeze`
  ("the work branch"), made by hand with `git worktree add -b <branch> <path>
  epic/tcw-3.0` from the then-current `epic/tcw-3.0` (the 3.0 CLI has no
  `--worktree`). Do not touch TCW-76's worktree. The primary checkout stays on
  `main`.
- **The board.** `docs/work/` on `main`, edited by hand or with the released
  2.8.x `tcw` (`source ~/.bashrc >/dev/null 2>&1;` first), never with the
  epic's code. Before Task 1 the item moves to `active/` on `main`. This
  item's `outcome.md` and `refined-outcome.md` are committed on `main`.
- **Which source runs.** A private virtual environment, never a re-pointed
  shared install: `python -m venv --system-site-packages <scratch>/prefreeze/venv`,
  `<scratch>/prefreeze/venv/bin/pip install -e <worktree> --no-deps`, and
  `<scratch>/prefreeze/venv/bin/pip install --ignore-installed pytest`. Run
  pytest and `tcw` with the worktree as the current folder and the venv's
  `bin` first on `PATH`. For Task 5, `pnpm install --frozen-lockfile` in the
  worktree.
- **Targeted tests only, never the full suite.** Each task runs the test files
  it names, every file under `tests/` that reads a file the task changed
  (`grep -rl '<file name>' tests`), and the standing guard files:
  `tests/test_cli_contract.py`, `tests/test_cli_help_standard.py`,
  `tests/test_static_guards.py`, `tests/test_cli_handler.py`,
  `tests/test_tree_store_raises.py`, `tests/test_no_node.py`,
  `tests/test_ledger_3_0.py`, `tests/test_documented_cli_surface.py`,
  `tests/test_doc_allowance.py` and `tests/test_shipped_text.py`.
  `pytest --collect-only -q` stays clean after every task.
- **New 3.0 tests only.** Add tests to the 3.0 test files beside the code's
  existing tests, or to new files. A 2.x test that breaks because 2.x behavior
  is gone is deleted or skipped, and listed in `outcome.md`.
- **Every new guard is mutation-checked**: break what it claims to observe,
  confirm it goes red for the stated reason, restore. Each task names its
  mutation; Task 9 records the results.
- **One commit per task** on the work branch, no co-author or session lines.
- **No 3.0 `tcw` against this repository.** Every check that needs a working
  `tcw` uses a fixture project in a scratch folder, with `HOME` and
  `XDG_CONFIG_HOME` pointed at scratch folders and `TCW_NO_PERSONAL_CONFIG=1`
  unless the test is about personal configuration.
- **No Jira and no network.** Every Jira test uses the fake
  (`tests/work/jira/fake.py`).
- **Approval is a bounded adversarial review** (Task 10), in place of the
  owner's verify.

## Blockers and ordering

- No blocker. TCW-76's freeze (its Task B3) waits for this item.
- TCW-76 Part A runs at the same time on its own branch. No file is changed
  by both (spec, "Overlap with TCW-76 Part A"). Task 7 widens two scans that
  read files Part A changes, so whichever item lands on `epic/tcw-3.0` second
  re-runs `tests/test_documented_cli_surface.py`,
  `tests/test_docs_describe_3_0.py` and `tests/test_shipped_text.py` over the
  merged tree before it lands.

## Tasks

### Task 1: The Jira backend (J1, J3, T4; criteria 1, 2, 27)

- **J1.** `tcw/work/jira/backend.py`: `_post_note` catches
  `TrackerUnavailable` separately and decides by `_note_found` (Design 1);
  the "may have been posted" message names `tcw work show <slug>`.
  `tcw/work/advance.py:288`: the suffix becomes "if it is missing, add it with
  `tcw work comment`". `tests/work/jira/fake.py`: a way to drop the connection
  after the next comment is received (`drop_after_next_comment(then_unreachable=…)`),
  since `drop_after_next_write` fires on the transition first.
- **J3.** `tests/work/jira/capture.py`: `record` sets every `timeZone` to
  `Etc/UTC` and every `locale` to `en_US` before scrubbing; the docstring says
  so. Rewrite the existing files in `tests/work/jira/recorded/` with the same
  values by a one-off script (no live run; values only, nothing else changes).
- **T4.** `tcw/work/jira/client.py`: `TrackerSiteMissing(TrackerError)`, and
  `_for_status` raises it for a 404 on `SITE_ENDPOINTS` (`/search/jql`,
  `/myself`, `/issuelinktype`, matched on the path without its query).
  `backend.py`'s `_jira()` maps it to `BackendError` with the Design 14
  message. `fake.py`: a `site_missing` switch answering 404 with an HTML body
  to every request.
- **Proves:** `tests/work/jira/test_jira_set_stage.py` (the three J1 cases),
  `tests/work/jira/test_recorded_shapes.py` (J3: values in the files, and
  `Recorder.record` on a synthetic body), `tests/work/jira/test_jira_errors.py`
  and `test_client.py` (T4: `work list` exit 1 with "check that
  work.jira.site"; a ticket 404 still exit 4), and `test_fake.py`,
  `test_jira_advance.py`.
- **Mutations:** `_post_note` posts without looking (the "found" case shows
  two comments); `record` stops replacing `timeZone`; `_for_status` drops the
  `SITE_ENDPOINTS` branch.

### Task 2: Personal configuration (P1, P2, P3, P5; criteria 3, 4, 5, 7)

- **P1.** `tcw/store/yaml_source.py`: `_no_dup_keys` catches `TypeError` from
  an unhashable key and raises `yaml.constructor.ConstructorError` with the
  key's `start_mark`, so the error names the file and line ("a mapping key
  must be a single value, not a list or mapping"). Update the `load`
  docstring's list of errors that name no file.
- **P2.** `tcw/config.py` `_merge`: when `value` and `lower` are both empty
  mappings, the origin becomes the current layer.
- **P3.** `tcw/work/jira/config.py` `_credentials`: check both keys, add a
  problem for each bad one, then return `None` if any was bad.
- **P5.** `tcw/config_cli.py` `_scalar`: `bytes` as `!!binary "<base64>"`;
  `set` and `frozenset` as `!!set {<sorted members>: null, …}` through `_flow`.
- **Proves:** a new `tests/test_config_edges.py` (P1 for the project file and
  the local file, through the CLI, asserting exit 1, the file name, and no
  `Traceback`; P2 through `config show --origin`; P5 round trip through
  `yaml.safe_load` and a one-line check), `tests/work/jira/test_jira_config.py`
  (P3). Not `tests/test_cli_config.py`, which TCW-76 changes.
- **Mutations:** remove the `TypeError` catch; remove the P2 restamp; restore
  P3's early return; restore `_scalar`'s old non-string branch.

### Task 3: The CLI and the stores (P4, C1, C2, C4, C7, C8, C9, T2; criteria 6, 8, 9, 11, 13, 14, 15, 25)

- **P4.** `tcw/work/cli.py` `_new`: when `--project` is absent, open the
  backend and call `creation_stage` before `read_piped_stdin`; drop the later
  duplicate call.
- **C1.** `tcw/store/fs.py`: a helper `_nested_entries(d)` used by `remove`
  and `reset`; `reset` refuses with exit 3 (Design 3).
- **C2.** `tcw/store/base.py`: `is_slug(text)` beside `slugify`.
  `FsTaxonomyStore.add` raises `UsageError` (Design 4) when `slug` is given
  and is not one. Also check the viewer's create route answers 400.
- **C4.** `tcw/store/fs.py` `FsStoreProvisioner._run`: the environment of
  Design 5; the `core.sshCommand` read goes through `_git` with
  `git config --get core.sshCommand` (a read).
- **C7.** `tcw/store/fs.py`: `_local_slugs` and `get_local` require
  `meta.yaml`; correct `remove`'s comment.
- **C8.** `tcw/store/fs.py` `refuse_retired_config`: name
  `os.path.relpath(root / SENTINEL)`.
- **C9.** `tcw/work/open.py` `open_backend`: `require_valid()` when
  `personal` is true.
- **T2.** `tcw/work/open.py` `uncommitted_changes`: "the work store of
  project '<id>'" / "the project's work store".
- **Proves:** the files holding each command's existing tests, found with
  `grep -rl` on the message or function (`--stage accepts only`, `reset`,
  `taxonomy add`, `_run`/`provision`, `_local_slugs`/`taxonomy list`,
  `was renamed to 'projects'`, `uncommitted_changes`), each with the new
  case: P4 asserts `read_piped_stdin` is never called (patched to fail);
  C9 includes the declared-but-absent child that must still exit 0; C4
  patches `_git` to capture the environment, with and without a preset
  `GIT_SSH_COMMAND`. Plus `tests/test_subprocess_stdin.py` and
  `tests/test_upstream_projects.py`.
- **Mutations:** move the stdin read back first; drop `reset`'s nested check;
  drop the slug check; drop the `_run` environment; restore `_local_slugs`;
  restore the bare `SENTINEL`; drop `require_valid()`.

### Task 4: Validate (T5, T7; criteria 28, 30)

- **T7.** `tcw/validate.py` `round_findings`: skip `layout.external`.
- **T5.** `tcw/validate.py` `_work_findings`, Jira branch: for each item
  folder (`jira_store_problems`'s scan of key-named folders) with a
  `capabilities.yaml`, `parse_declarations`; a `str` answer is an error at
  that file, worded as `records_problems` words it. `tcw/work/jira/remote.py`
  `_model_checks`: skip `records_problems` for a declaration that does not
  parse.
- **Proves:** `tests/work/jira/test_jira_validate_offline.py` (T5 malformed,
  well-formed, and a finished-item folder; T7 qa round),
  `tests/work/jira/test_jira_validate_remote.py` (T5 reported once with
  `--remote`), and the filesystem-mode round test (`grep -rl 'round is
  invalid' tests`).
- **Mutations:** remove the external skip (the qa warning returns); remove the
  offline parse check; remove the remote skip (two findings).

### Task 5: The viewer (V1, V2, V3, V5; criteria 16, 17, 18, 20)

- **V1.** `tcw/serve/records.py:112` and `:188`: `request.field("revision")`,
  required. Update any viewer test that sends a `PATCH` without it.
- **V2.** `tcw/serve/files.py` `file_path`: resolve and contain (Design 10).
- **V3.** `tcw/store/project.py:58-60`: the comment says the cache lives as
  long as the process, a whole server run under `tcw serve`, and that a
  directory added or removed as a linked worktree while a server runs is seen
  after a restart.
- **V5.** `web/client/src/ui/content-views.tsx` `Conflict`: `Callout.Text`
  holds the heading and sentence only; the buttons' `Flex` moves beside it
  in `Callout.Root`. Then `pnpm build`, and commit `tcw/serve/dist` with the
  source.
- **Proves:** the viewer tests for records and files (`grep -rl
  'api/taxonomy\|api/capabilities\|files.py\|/files/' tests/serve`), with the
  V1 and V2 cases (V2 asserts nothing appears in the outside folder); a vitest
  test rendering `Conflict` with `console.error` watched; `pnpm test`,
  `pnpm check:build`, `pnpm typecheck` if present; `tests/serve/test_static.py`.
- **Mutations:** `required=False` again; drop the containment check (the file
  appears outside); restore the nesting (the vitest test sees the warning).

### Task 6: Text and docstrings (T1, T3, V7, V8; criteria 22, 23, 24, 26)

- **T1.** `tcw/work/generate.py:180`, `:184`: `work.hooks.output-cap`,
  `work.hooks.timeout`.
- **T3.** `tcw/work/hooks.py:8-10` (the viewer runs no `pre` hooks and moves
  no item; adopting a Jira ticket runs the request stage's `post` hooks, as
  `tickets adopt` does); `tcw/cli.py` `run_provision` (the only command that
  clones a repository; the Jira backend's commands also reach the network, to
  the configured site only); `tcw/store/base.py:5-6` (the filesystem adapters
  are the only store adapters for taxonomy and capabilities; the work axis
  also has a Jira backend); `skills/README.md:85` (drop "TCW-75 rewrites this
  skill").
- **V7.** `docs/guide/work.md`, "Built-in gates": no gate checks that a
  stage's document exists; a project that wants one adds a `pre` hook on the
  next stage, as TCW's own `tcw-config.yaml` does with
  `scripts/require_artifact.py`. Link to the configuration guide's hook
  section rather than to the script, which TCW-76 changes.
- **V8.** `tcw/work/procedures/unattended-work.md`: the request row (Design
  13). `skills/extras-autonomous-work/SKILL.md`: the same rule only if it
  lists stages itself.
- **Proves:** a test that the `GenerateError` messages name `work.hooks.*`
  (beside the existing `generate` tests); `grep -rn` for each old phrase finds
  nothing; `tests/test_shipped_text.py`, `tests/test_docs_describe_3_0.py`,
  `tests/test_procedure_verb.py`, `tests/test_prompt_fallback.py` and any
  test reading `unattended-work.md` (`grep -rl unattended tests`).
- **Mutations:** none; no guard is added.

### Task 7: The scans (C3, C6, V4, V6, T6; criteria 10, 12, 19, 21, 29)

- **C3.** `tests/work/test_git_write_scan.py`: add the eight verbs; skip the
  value after `-C`, `-c`, `--git-dir`, `--work-tree` and `--namespace` when it
  is a separate element; key `ALLOWED` on `"FsStoreProvisioner._obtain"`,
  matched against the enclosing class and function; a test that every `git`
  literal whose verb is `status` has `--no-optional-locks` before the verb;
  update the docstring.
- **C6.** `tests/conftest.py`: put `Path(sys.executable).parent` first on
  `PATH` when it holds `tcw`, with a comment saying why; a test of criterion
  12.
- **V4.** `tests/serve/test_no_stage_names.py`: scan inside `${…}`; check
  unquoted object keys and member names; treat `/` after a keyword
  (`return`, `typeof`, `case`, …) as a regex. A key or member that equals a
  stage name today is either fixed in the client (Task 5's rebuild then
  covers it; if Task 5 is committed, rebuild again here) or listed in a named
  allowance with its reason. Scanner tests for each.
- **V6.** `tests/test_documented_cli_surface.py`: paragraph-wide code spans
  (Design 11); update the comment at lines 74-82. Fix or reword any command
  the wider scan newly finds invalid.
- **T6.** `tests/doc_vocabulary.py` `scan`: paragraph-wide (Design 16). Fix or
  reword any newly found phrase in the scanned documents.
- **Proves:** each changed test file, plus `tests/test_shipped_text.py`,
  `tests/test_configuration_text_home.py`, `tests/test_docs_describe_3_0.py`
  (the users of `scan`), and the three files that compare an in-process
  `import tcw` with a `tcw` subprocess: `tests/test_stage_verb.py`,
  `tests/test_procedure_verb.py`, `tests/test_prompt_fallback.py`.
- **Mutations:** C3: remove the `-c` value skip; remove `switch` from the
  verbs and plant `["git", "switch", "x"]`; re-key the allowance on the class
  and plant a `clone` in another method; remove `--no-optional-locks` from
  `tcw/store/fs.py:179`. C6: remove the prepend and run with a folder first
  on `PATH` holding a `tcw` script that prints a 2.x message. V4: plant a
  stage name in each of the three positions in a client file. V6: restore the
  one-line pattern. T6: restore line-by-line scanning.

### Task 8: Documentation sync and release entries (criterion 31)

Invoke the `documentation-sync` skill against the branch's
`tcw-config.yaml` `work.documentation` entries (read the file; do not run the
3.0 `tcw work docs` against this repository). Expected updates, each read
against the code after Tasks 1 to 7:

- `docs/guide/jira.md`, "Checking the workflow" (lines 151-155): offline
  validation also reads each item folder's `capabilities.yaml` and reports one
  that is malformed; the records check stays under `--remote` (T5). Where the
  guide describes a failed note after a move, the "may have been posted"
  case (J1). Where it describes errors, the missing-site message (T4).
- `docs/guide/linking-and-validation.md`, "Work items" (lines 84-91): the
  same T5 change; the `capabilities.yaml` check moves from "run only under
  `--remote`" to "the file's form offline, the records under `--remote`".
- `skills/configure/references/jira.md`, "Checking the configuration against
  Jira" (lines 187-188), if it lists what offline validation reads.
- `docs/guide/taxonomy-and-capabilities.md`: `--slug`'s form (C2, near line
  27); a term is a folder holding `meta.yaml` (C7, near line 74); `reset`
  refuses when local capabilities sit under the override (C1, near line 235).
- The guide section that describes `tcw provision` (`grep -rln 'tcw provision'
  docs/guide skills/configure/references`): it never asks for a password; a
  private repository needs a credential helper or an ssh agent (C4).
- `docs/guide/work.md` "Built-in gates" is Task 6's.
- README: likely nothing; confirm.
- `docs/changelogs/upcoming/<slug>.md` and `docs/release-notes/upcoming/<slug>.md`
  (`<slug>` is this item's), each listing the user-facing changes: J1, P1,
  P3, P4, P5, C1, C2, C4, C7, C8, C9, V1, V2, T2, T4, T5, T7.
- **Proves:** `tests/test_docs_describe_3_0.py`, `tests/test_shipped_text.py`,
  `tests/test_doc_allowance.py`, `tests/test_documented_cli_surface.py`,
  `tests/test_configuration_text_home.py`, and any test naming a changed
  document.

### Task 9: Mutation record and collection (criterion 32)

Run `pytest --collect-only -q`. Write `outcome.md` on `main`: each mutation
from Tasks 1 to 7, whether it went red and for what reason, and any 2.x test
deleted or skipped. Commit on `main`.

### Task 10: Review, landing and closing

1. **Review.** One `adversarial-code-reviewer` round over
   `git diff <base>..work/<slug>` with `spec.md` and this plan, bounded per
   the epic rule: findings sorted into "belongs to this change" and "needs a
   separate change", ending with DONE or NOT DONE. Fix what belongs here in
   one round (a commit per fix round), then one confirming round. If that is
   still NOT DONE, stop and report to the owner rather than looping.
   Separate-change findings that touch `tcw/` are raised with the owner at
   once, since the freeze follows.
2. **Land.** If `epic/tcw-3.0` moved since the worktree was made, rebase the
   work branch onto it and re-run every task's tests plus the cross-scan
   check under "Blockers and ordering". Then fast-forward:
   `git -C /Users/brian/Projects/TCW fetch . work/<slug>:epic/tcw-3.0`
   (refuses anything but a fast-forward). Do not push.
3. **Close on `main`.** `refined-outcome.md` records the review rounds and the
   rule used; the J2 inbox entry is written to `docs/work/inbox/` (the two
   unseen shapes, what recording them needs, and owner question 1's answer if
   given); the item moves to `completed/`. Restore nothing in the shared
   install, which this plan never re-points; remove the worktree after
   landing.

## Verification

| Criterion | Task | Criterion | Task |
| --- | --- | --- | --- |
| 1, 2 | 1 | 17, 18 | 5 |
| 3, 4, 5 | 2 | 19 | 7 |
| 6 | 3 | 20 | 5 |
| 7 | 2 | 21 | 7 |
| 8, 9 | 3 | 22, 23, 24 | 6 |
| 10 | 7 | 25 | 3 |
| 11 | 3 | 26 | 6 |
| 12 | 7 | 27 | 1 |
| 13, 14, 15 | 3 | 28 | 4 |
| 16 | 5 | 29 | 7 |
| 30 | 4 | 31 | 8 |
| 32 | 9 | | |
