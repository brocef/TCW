# Spec — Core work model: stage table, item folders that never move, and advance

## Capability changes

**None in this slice.** This slice adds TCW 3.0's work model as a library: new
modules with tests, wired into no command. Nothing a user can run changes, so no
capability record changes. The records describing the 3.0 work axis (the work
lifecycle, `advance`, the `node`, `transition` and `definition-of-done` taxonomy
terms) change in the slices that ship the behavior: TCW-70 wires the model into
the CLI with the filesystem backend, and TCW-73 finishes the command surface.
The ledger has one `work/` capability today
(`work/archive-a-resolved-item-before-it-is-deleted`). TCW-70 removes it,
because 3.0 never deletes item folders.

## Problem

TCW 2.8's work model owns facts in two places and hard-codes its lifecycle
throughout ~30,000 lines. Five problems follow.

1. **Status is a folder location.** `_status_of` returns the first path
   component under the work root (`tcw/store/fs.py:4787-4790`). Every move is a
   `git mv` plus a commit (`fs.py:8219`, `fs.py:8249-8294`). A move is therefore
   a git operation, and a branch that moved an item conflicts with one that
   edited it.
2. **Stages and statuses are two hard-coded ladders.** The ladders are:
   - `WORK_STATUSES` (`tcw/store/base.py:989`);
   - `LEGAL_TRANSITIONS` (`base.py:1006-1015`);
   - `STAGE_STATUSES` (`base.py:2301-2309`);
   - `STAGE_IDS` and `TRANSITION_IDS` (`base.py:1136`, `base.py:1155`).

   Stage names are literals in at least six modules: `store/base.py`,
   `work/cli.py`, `store/fs.py`, `work/resolve.py`, `work/recursion.py` and
   `work/templates.py`. A project cannot add a stage or disable one.
3. **Moving an item takes five verbs, each with its own gates.** The verbs are
   start, submit, rework, complete and drop (`tcw/work/cli.py:1586`, `:1747`,
   `:1778`, `:4191`, `:4520`). Each runs a different mix of claims, blocker
   checks, worktree merges, DoD confirmation, capability gate, tracker sync,
   retention deletes and commits. `_complete` alone runs about a dozen checks
   in a fixed order (`cli.py:4225-4514`).
4. **The capability gate assumes planned records.** It treats a `new:` path as
   seeded at planning with status `Missing` and requires it flipped by
   completion (`tcw/work/recursion.py:153-160`). That makes `Missing` mean
   "planned" as well as "known gap". It also runs only at completion
   (`cli.py:4443`), after the code that should have changed the records has
   long been reviewed.
5. **The store interface is too large for a second backend to implement.**
   `WorkStore` (`base.py:3386`) has about 35 abstract methods, among them
   graveyard, plan stages, sidecars, DoD and inbox. Its lifecycle methods are
   built on filesystem assumptions. No non-filesystem implementation exists
   besides a test stub (`tests/test_retention.py:942`). This fails the
   repository's own abstraction litmus test in practice.

## Goals

1. **One definition of a work item.** The definition covers:
   - its identity: the slug `{project id}/{folder}`;
   - one property set: title, stage, priority, effort, complexity, tags,
     assignee, parent, blocked-by;
   - the creation date, which is read from the backend and never stored as a
     property.
2. **Stages as data.** One built-in stage table, which no other module names a
   stage outside of. Each project can disable the optional stages.
3. **One move operation.** `advance` decides the target, runs the target stage's
   gates, moves, records forced moves and discards as comments, and runs
   `post` hooks. It returns an outcome that maps onto TCW-73's exit codes.
4. **Two built-in gates that run during the lifecycle.** The records gate checks
   that the declared capability and taxonomy changes are in the records after
   implement. The completion gate checks that the verification rounds were
   accepted.
5. **A shared item-folder layout.** Item folders never move. Each stage's files
   sit in a stage folder: a revised document, or numbered rounds with
   verdicts, plus timestamped handoffs. Paths are computed in one place.
6. **A seven-operation backend interface** that both TCW-70 and TCW-71 can
   implement: create, read, list, update properties, set stage, comment,
   rename.
7. **The `work.stages` configuration shape** is parsed and validated, and
   unknown or removed keys are errors.
8. **No git state changes** anywhere in the new code.

## Non-goals

- **Wiring into the CLI.** No command changes behavior in this slice. TCW-70
  connects the model to `tcw work` with the filesystem backend and removes
  the 2.x work store. TCW-73 owns the final command surface, the stdout/stderr
  contract and the exit-code table. This slice defines the exit codes as
  constants, because `advance` must return them.
- **Backends.** This slice does not cover:
   - the filesystem storage details (`item.yaml`, date-prefixed folder names,
     inbox items, comment files, rename's reference rewriting): TCW-70;
   - everything Jira: TCW-71.

  Tests use an in-memory backend that lives under `tests/`. It is not shipped.
- **Personal config and the `inherit` chain** (TCW-72). This slice parses the
  `prompt`, `pre`, `post` and `procedures` lists with today's binding parser
  (`base.py:2525`) and today's `builtin: true` marker. TCW-72 replaces that
  marker with `inherit`.
- **Renaming "node" to "project" across surviving code.** The new modules use
  "project" only. The sweep through code that outlives 3.0 (the project
  registry, `tcw work nodes`) happens in TCW-73, which already touches every
  surface. Code that 3.0 deletes is not renamed first.
- **Prompts, skills, documentation and migration:** TCW-74, TCW-75 and TCW-76.
- **The 2.x code.** None of it is changed or removed here. The two models
  coexist until TCW-70 switches over.

## Design

The new code lives in `tcw/work/` beside the 2.x modules, under names that do
not collide:

- `model.py`: identity, properties, the stage table;
- `config.py`: `work.*` parsing;
- `layout.py`: item-folder paths and round verdicts;
- `backend.py`: the backend protocol and errors;
- `gates.py`: the built-in gates;
- `advance.py`: the move operation;
- `references.py`: reference checks for `validate`.

Exit codes go in `tcw/exit.py` because all three axes use them.

### 1. Identity (`model.py`)

1. `Slug(project: str, folder: str)`. Its text form is `project/folder`.
   - `project` matches the existing ID rule (`tcw/store/project.py:45-54`).
   - `folder` matches `^[A-Za-z0-9][A-Za-z0-9-]*$`, at most 128 characters.
     Mixed case allows Jira keys such as `TCW-67-…`. Each backend narrows the
     pattern for the names it creates.
2. `Slug.parse(text, current_project)` accepts exactly two forms:
   - `project/folder`;
   - a bare `folder`, read as belonging to `current_project`.

   Anything else, including a status path or a nested path, is a usage error.
   Input as a Jira key is resolved by the Jira backend (TCW-71), not here.
3. `title_words(title)` turns a title into the part of a folder name after
   its prefix: lowercase `[a-z0-9-]`, runs of other characters collapsed to
   one `-`, trimmed to fit the length limit. Each backend adds its own prefix.
   There is no `-2` suffix: a name that already exists is refused (exit 3).

### 2. Properties (`model.py`)

1. `Item` is frozen and has these fields:
   - `slug`;
   - `title`;
   - `stage: str | None` (`None` means the backend reports no stage);
   - `created: date`;
   - `priority`;
   - `effort` and `complexity`;
   - `tags: tuple[str, ...]`;
   - `assignee: str | None`;
   - `parent: Slug | None`;
   - `blocked_by: tuple[Slug, ...]`.

   There is no history, resolution, type, initiative, owner, worktree, branch,
   schema version or stored slug.
2. The scales are named and ordered:
   - `PRIORITIES = (highest, high, medium, low, lowest)`;
   - `SIZES = (low, medium, high, very-high)`, used for both effort and
     complexity.

   `new` defaults priority to `medium`. Effort and complexity have no default.
3. `Changes` is a partial update. It sets, clears or edits each property, and
   adds or removes tags and blockers. `stage` is not part of it: only
   `advance` moves an item.
4. Validation is shared by both backends:
   - a value outside its scale is a usage error;
   - a tag outside the project's registry is a usage error;
   - a `blocked-by` entry or a `parent` that is not a slug is a usage error;
   - an item that is its own parent or its own blocker is refused.
5. `blocks` is not stored. `blocks_of(item, items)` scans for items whose
   `blocked_by` names `item`. `edit --blocks X` becomes an update of X's
   `blocked_by`.
6. An item whose children are `list(parent=slug)` is an epic. There is no type
   flag and no depth limit.

### 3. The stage table (`model.py`)

1. `STAGES` is a tuple of `Stage` records with these columns:
   - `name`;
   - `kind`: `flow`, `terminal` or `side`;
   - `artifact`: `document`, `rounds` or `none`;
   - `optional`: whether the stage can be disabled;
   - `verdict`: whether its rounds carry a verdict;
   - `on_reject`: the stage a rejected round sends the item back to;
   - `gates`: the names of its built-in gates.

   Order is tuple order.

| name | kind | artifact | optional | verdict | on_reject | gates |
| --- | --- | --- | --- | --- | --- | --- |
| inbox | flow | none | no | no | – | – |
| request | flow | document | no | no | – | – |
| spec | flow | document | yes | no | – | – |
| plan | flow | document | yes | no | – | – |
| implement | flow | rounds | no | no | – | – |
| review | flow | rounds | yes | yes | implement | – |
| qa | flow | rounds | yes | yes | implement | – |
| completed | terminal | none | no | no | – | completion |
| discarded | terminal | none | no | no | – | – |
| postmortem | side | document | yes | no | – | – |

2. **No other module contains a stage name as a literal.** Behavior comes
   from the columns, not from names. Three cases show how:
   - **The records gate** attaches to the stage that follows the last
     unverdicted rounds stage, which today is implement. That following
     stage is the next enabled flow stage. If no flow stage is enabled after
     it, the gate attaches to the first terminal stage.
   - **"Back to implement"** reads `on_reject`.
   - **The completion target** is the first terminal stage, which is how
     `completed` is found.
     **[Decision]** `discard` targets the stage named `discarded`. This is the
     table's only named lookup, kept as one constant beside the table.
3. **The enabled set** is the table minus the optional stages a project
   disabled. A side stage is never the target of `advance`, which refuses it
   as a usage error. It has a folder, a prompt and an artifact, and never
   changes `stage`.
4. **[Decision] Rounds without a verdict.** Implement rounds carry no verdict:
   the ticket listed `round-N.md with a verdict` for all three loop stages,
   but an implementation round has nothing to accept. Only `verdict: yes`
   stages have verdicts.

### 4. Item-folder layout (`layout.py`)

1. The item folder is `<work path>/<folder>`. It is created by the backend's
   `create`, never moved by TCW, and never deleted by TCW.
2. Only stages whose artifact is not `none` get a folder: `<item>/<stage>/`.
3. A document stage's file is `<stage>/<stage>.md`. The spec stage also has
   `spec/capabilities.yaml`.
4. A rounds stage's files are `<stage>/round-N.md`, numbered from 1 per stage.
   `next_round(stage)` is one more than the highest existing `N`. Gaps are
   allowed, and the highest `N` is the latest round.
5. A round in a verdict stage starts with YAML front matter carrying
   `verdict: accepted | rejected`. `round_verdict(path)` returns `accepted`,
   `rejected` or `invalid`. `invalid` covers no front matter, a missing key or
   any other value, and the completion gate treats it as not accepted.
6. Handoffs are `<stage>/handoff-<YYYYMMDDTHHMMSSZ>.md`, in UTC. The newest by
   name wins.
7. `path(slug, stage=None, next=False)` gives the item folder, the stage's
   document or folder, or with `next` the next round's path. This is the
   function behind `tcw work path` (TCW-70 wires the command). It never
   creates anything.
8. A stage whose record the backend keeps outside the folder has no files on
   disk: the request and qa in Jira mode. The backend declares this as
   `external_stages`, and `path` refuses such a stage (exit 3) with a message
   naming the backend.

### 5. Backend interface (`backend.py`)

```python
class WorkBackend(Protocol):
    project: str                          # tcw-config id
    external_stages: frozenset[str]       # stages whose record lives in the backend
    inbox_items: bool                     # may an item sit at the first stage?

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None) -> Item: ...
    def read(self, folder: str) -> Item: ...
    def list(self, query: Query) -> list[Item]: ...
    def update(self, folder: str, changes: Changes) -> Item: ...
    def set_stage(self, folder: str, stage: str) -> None: ...
    def comment(self, folder: str, text: str) -> None: ...
    def rename(self, folder: str, title_words: str) -> Item: ...
```

1. `Query` fields are:
   - `stages` (default: all non-terminal stages, so finished items are
     hidden);
   - `parent`;
   - `assignee`;
   - `include_finished`.
2. Errors are exception classes carrying an exit code:
   - `NotFound` (4);
   - `Refused` (3);
   - `Unreachable` (5);
   - `UsageError` (2);
   - `BackendError` (1).
3. Each operation is atomic as far as the backend allows, and changes only
   what it names. `create` makes the folder. `set_stage` neither checks
   anything nor runs hooks, because that is `advance`'s job.
4. **Not in the interface:**
   - layout, paths and artifacts, which are shared files;
   - DoD, graveyard, retention, claims, plan stages, sidecars, the inbox
     verbs and tracker sync, all of which 3.0 removes.

### 6. Moving: `advance` (`advance.py`)

`advance(backend, config, slug, to=None, force=False, reason=None, dry_run=False) -> Outcome`
runs these steps in order.

1. **Usage checks** (exit 2):
   - `force` without a non-empty `reason`;
   - a `to` that is not in the table, is disabled, or is a side stage.
2. **Read** the item. `NotFound` gives exit 4.
3. **Choose the target.**
   - A given `to` is the target.
   - With no `to`, the target depends on the current stage:
     - no stage: refused (exit 3);
     - a terminal stage: refused (exit 3);
     - a verdict stage whose latest round is `rejected`: that stage's
       `on_reject`;
     - otherwise: the next enabled flow stage. If there is none, the first
       terminal stage.
   - A target equal to the current stage is refused (exit 3) as a no-op.
4. **Check direction.**
   - **Skips.** A move to a later stage that passes at least one enabled flow
     stage between the current stage and the target is a skip. A skip is
     refused (exit 3) unless `force`.
   - The completion stage counts as a later stage: moving from spec to
     `completed` with plan and implement enabled is a skip.
   - Moving back is never a skip.
   - Moving to the discard stage is never a skip, and needs no `force`.
   - **No stage.** A move from no stage needs `force`, because without a
     stage there is nothing to measure a skip from.
5. **Gates.** These run only for the target:
   - the target's built-in gates;
   - then its configured `pre` bindings, through the existing runner
     (`tcw/work/hooks.py:73`).

   The hook environment has `TCW_SLUG`, `TCW_STAGE` (the target),
   `TCW_FROM_STAGE` (empty when there is none), `TCW_ITEM_PATH`,
   `TCW_PROJECT_ROOT`, and `TCW_FORCED` and `TCW_REASON` when forced. Hooks
   run in order and stop at the first failure.
   - A failure refuses the move (exit 3), unless `force`.
   - With `force`, a failure is reported on stderr and the move continues.
6. **Dry run** stops here. It returns OK when the move would happen, and the
   refusal otherwise.
7. **Move** with `backend.set_stage`.
8. **Trace.** A forced move, or any move to the discard stage, posts one
   comment through `backend.comment`. The comment names the source and target
   stages, says whether the move was forced, gives the reason, and lists any
   gate failures that were overridden.

   Moving to the discard stage requires a reason even without `force`
   (`discard <slug> --reason`).

   If the comment fails, the move stands. The error names the missing trace,
   and the exit code is that of the comment's error.
9. **`post` bindings** run. A failure keeps the move and returns exit 6.
10. **Result.** The outcome carries the new stage. TCW-73 prints it on stdout.

Creating an item (`new`, adopt, delegation) is not a move and runs no gates.
`new` starts at `request`. It may start at `inbox` only when
`backend.inbox_items` is true, which the filesystem backend sets.

### 7. Built-in gates (`gates.py`)

**The records gate.** It reads `spec/capabilities.yaml`. A missing file
declares nothing and passes. The schema is:

```yaml
new: [<capability path>, ...]
changed: [<capability path>, ...]
removed: [<capability path>, ...]
taxonomy:
  new: [<term>, ...]
  changed: [<term>, ...]
  removed: [<term>, ...]
```

Every key is optional, and an unknown key is an error. The deprecated
`added:` alias goes (it is accepted today at `base.py:364-401`).

The gate checks the declared changes against the records:

- each `new` or `changed` capability path resolves;
- each `new` path does not have status `Missing`;
- each `removed` path does not resolve;
- each `new` or `changed` term exists;
- each `removed` term does not exist.

Paths are routed to the ledger that answers for them by today's rule
(`route_capability_path`, `recursion.py:204-253`). The routing moves into
`gates.py`, and an inherited `removed` path is still a problem. An unreadable
or malformed file fails the gate. The gate replaces `capability_gate`
(`recursion.py:50-165`) and its planned-`Missing` assumption.

**The completion gate.** For each enabled verdict stage that is not in
`backend.external_stages`, the latest round must be `accepted`. A stage with
no rounds fails. In Jira mode the qa verdict is the status move itself, so
only review is checked there.

**Drift.** `drift_problems(items)` takes completed items and re-checks their
`spec/capabilities.yaml` declarations against the records today.

- A path every completed item declares `new` or `changed`, and that no longer
  resolves (or is `Missing`), is drift.
- A path every completed item declares `removed`, and that resolves again, is
  drift.
- A path declared both ways is not reported, because nothing records which
  item came last.

This replaces `_shipped_but_missing` (`tcw/capabilities/cli.py:200`). TCW-73
wires it into `capabilities drift`.

**No Definition of Done.** No gate reads `dod.yaml`.

### 8. Configuration (`config.py`)

`parse_work_config(mapping) -> (WorkConfig, problems)` accepts exactly these
keys under `work`:

- `path`;
- `repository`;
- `backend` (`filesystem` or `jira`, default `filesystem`);
- `tags`;
- `documentation`;
- `procedures`;
- `stages`;
- `jira`, passed on unparsed to TCW-71's backend.

Each `work.stages.<stage>` takes:

- `enabled`: refused on a stage whose `optional` is no;
- `status`: a non-empty string, kept for the Jira backend;
- `prompt`;
- `pre`;
- `post`.

The checks:

1. An unknown stage name is an error.
2. A stage key outside the five above is an error.
3. The removed 2.x keys are errors that name the migration guide:
   - `work.lifecycle`;
   - `work.tracker`;
   - `transitions`;
   - `auto-commit-transitions`;
   - `publish-transitions`;
   - `trunk-branch`;
   - `retain`.
4. Any other unknown key under `work` is an error.
5. In Jira mode, two enabled stages with the same `status` are an error.
   Every enabled stage must have one, except `postmortem`, whose kind is
   `side`. Side stages take no status.

### 9. References (`references.py`)

`reference_problems(items, resolve)` checks every `parent` and `blocked-by`
entry.

- A slug in this project that does not exist is a **warning**: "references a
  missing item".
- A slug in another project goes through `resolve`, which answers `found`,
  `missing` or `unresolved`. `unresolved` means the project cannot be reached
  from here. It is reported as unresolved and is neither a warning nor an
  error.

**[Decision on the open question] Stage ahead of artifacts.** `stage_problems`
checks each item. Any enabled document or rounds stage that comes before the
item's stage, is not external, and has no artifact is a **warning**. It
applies in both modes. In Jira mode it runs under `validate --remote`,
because reading the stage needs the network.

### 10. Git

None of the new modules imports `subprocess` or the git helpers in
`tcw/store/fs.py`, except the hook runner they reuse. They write only the files
they name.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| create, read, list, update, set stage, comment, rename | **Backend interface.** Jira implements each one: issue create, get, JQL, edit, transition, comment, summary edit. |
| `advance`, gates, `discard` | **Model.** Built only on the interface and the layout. |
| Item-folder layout, rounds, handoffs, `path` | **Shared layout**, not an interface operation. Git owns technical artifacts in both modes, so the files exist in both. |
| `external_stages`, `inbox_items` | **Backend facts.** These are declared, not detected. |
| Records gate, drift | **Model,** over the capabilities and taxonomy stores' abstract interfaces. |
| `blocks` | **Derived by query.** Nothing stores it. |

## Acceptance criteria

All criteria are checked by pytest tests in `tests/work/`, against the in-memory
backend (`tests/work/memory_backend.py`) and temporary directories.

1. **Identity.**
   - `Slug.parse` accepts `p/f` and a bare `f`.
   - It rejects `a/b/c`, `backlog/f`, an empty value, a folder with `_` or
     spaces, and a folder longer than 128 characters.
   - `str(Slug.parse("tcw/TCW-67-x", "tcw")) == "tcw/TCW-67-x"`.
2. **Title words.**
   - `title_words("Make tcw validate usable: a gate!") == "make-tcw-validate-usable-a-gate"`.
   - The output is at most the folder limit minus a 20-character prefix
     allowance.
3. **Properties.** Each of these is a `UsageError`:
   - a priority outside the five names (including an integer);
   - effort `huge`;
   - a tag not registered;
   - a free-text blocker.

   Each of these is `Refused`:
   - an item set as its own parent;
   - an item set as its own blocker.
4. **Blocks are derived.** After `edit --blocks` semantics (updating B's
   `blocked_by` with A), `blocks_of(A)` returns `[B]`, and A's own record is
   unchanged.
5. **No literal stage names.** A test scans `tcw/work/{advance,gates,layout,
   backend,references,config}.py` and `tcw/exit.py`. None contains any stage
   name as a string literal. `model.py` contains them only inside `STAGES` and
   the discard constant.
6. **Disabling stages.**
   - With review and qa disabled, a bare `advance` from implement targets
     `completed`.
   - With plan disabled, a bare `advance` from spec targets implement.
   - Disabling `implement` or `request` is a config error.
7. **Bare advance.**
   - It goes from request to spec.
   - From review with latest round `rejected`, it goes to implement.
   - From review with latest round `accepted` (and qa enabled), it goes to qa.
   - From qa with latest round `rejected`, it goes to implement.
   - From a terminal stage it is `Refused` (exit 3).
   - From no stage it is `Refused`.
8. **Skips and backward moves.**
   - `--to implement` from spec (plan enabled) is `Refused` without force.
   - `--to completed` from spec, with review and qa disabled, is `Refused`
     without force. That move skips plan and implement.
   - With `force` and a reason, it moves and posts one comment containing
     the reason.
   - `--to spec` from review moves without force and posts no comment.
   - `--to discarded` from any stage needs a reason, moves, and posts one
     comment.
   - `--to postmortem` is a `UsageError`.
   - `force` with no reason is a `UsageError`, and the backend records no
     call.
9. **Gates run for the target only.**
   - A failing `pre` on review refuses a move into review (exit 3), and the
     backend's stage is unchanged.
   - A failing `pre` on spec does not affect a move from spec to plan.
   - With `force`, the failing gate is overridden, the move happens, and the
     comment names the overridden gate.
10. **Post hooks.** A failing `post` returns exit 6, and the backend's stage
    is the target.
11. **Dry run.** It runs the gates and returns the would-be outcome. The
    backend records no `set_stage` and no `comment` call.
12. **Missing stage.** An item whose backend stage is `None` is moved by
    `--to spec --force --reason r` and refused without `force`.
13. **Records gate.** Each of these cases is a failure:
    - a `new` path that does not resolve;
    - a `new` path with status `Missing`;
    - a `removed` path that still resolves;
    - a `taxonomy.new` term that is absent;
    - an unknown key;
    - unreadable YAML.

    A missing file passes. The gate is attached to review, and to
    `completed` when review and qa are disabled.
14. **Completion gate.** Each of these refuses `completed`:
    - no review round;
    - latest review round `invalid`;
    - review accepted but latest qa `rejected`.

    With `external_stages = {request, qa}`, only review is checked.
15. **Layout.**
    - `path(slug, "review", next=True)` is `round-3.md` when rounds 1 and 2
      exist, and `round-1.md` when none do.
    - Handoff names match `handoff-\d{8}T\d{6}Z\.md`.
    - `path` for an external stage is `Refused`.
    - `path` creates nothing on disk.
16. **Config.**
    - Each removed 2.x key is an error naming the migration guide.
    - An unknown `work.*` key is an error.
    - An unknown stage, or an unknown key on a stage, is an error.
    - Two enabled stages with one `status` in Jira mode is an error.
    - The repository's current `tcw-config.yaml` reports
      `lifecycle`, `tracker` and `retain` as removed. This is expected: TCW-76
      migrates it.
17. **References.**
    - A missing same-project `blocked-by` is a warning.
    - A cross-project ref whose project cannot be resolved is reported as
      unresolved and not as a warning.
    - An item at `plan` with no `spec/spec.md` (spec enabled) gets the
      stage-ahead warning. With spec disabled, it does not.
18. **Drift.**
    - A completed item declaring `new: [x/y]` while `x/y` is absent is
      drift.
    - If another completed item declares `removed: [x/y]`, it is not.
19. **No git.** A test asserts that none of the new modules imports
    `subprocess`, except through `tcw.work.hooks`, and that none references
    the git helper names in `tcw/store/fs.py`.
20. **2.x untouched.** The full existing test suite passes unchanged.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Identity | 1, 2 |
| 2 Properties | 3, 4 |
| 3 Stage table | 5, 6, 8 (side stage) |
| 4 Layout | 15 |
| 5 Backend interface | Exercised by 7–14 through the memory backend. Atomicity is per backend, so it is n/a here; TCW-70 and TCW-71 own it. |
| 6.1 Usage | 8 |
| 6.2 Read | 12; `NotFound` in 7 (unknown slug) |
| 6.3 Target | 7 |
| 6.4 Direction | 8, 12 |
| 6.5 Gates | 9 |
| 6.6 Dry run | 11 |
| 6.7–8 Move and trace | 8, 9 (comment names the gate) |
| 6.9 Post | 10 |
| 7 Gates | 13, 14, 18 |
| 8 Config | 6, 16 |
| 9 References | 17 |
| 10 Git | 19 |

Criterion 7 also checks that `advance` on an unknown slug returns `NotFound`
(exit 4).

## Risks

- **Two models coexist until TCW-70.** The new code is unused in production
  until then, so a design mistake may surface late. Mitigation: the memory
  backend exercises every path, and TCW-70 starts right after this slice.
- **The column-driven stage rules are subtle.** An example is "first enabled
  flow stage after the last unverdicted rounds stage". A future custom stage
  could make them read wrongly. Mitigation: criterion 5 forbids name literals,
  and criteria 6 and 13 pin the rules under disabled stages.
- **Records-gate timing.** Running at the stage after implement means an item
  forced past review skips the records check. That is accepted: forcing is
  deliberate and leaves a comment.
- **Drift without completion order** cannot judge paths declared both ways.
  Mitigation: those paths are skipped rather than guessed, as the design says.
- **Comment failure after a forced move** leaves a move with no trace.
  Mitigation: the error names it, so the caller can comment by hand with
  `tcw work comment`.

## Notes

- **Decisions made in this spec, for the owner to confirm:**
  - the model lands as a library and TCW-70 wires it in;
  - implement rounds carry no verdict;
  - discard requires a reason;
  - the taxonomy keys in `capabilities.yaml`;
  - drift skips paths declared both ways;
  - "stage ahead of artifacts" is a warning in both modes;
  - the "node" sweep goes to TCW-73.
- **The ticket's open questions** are answered in Design 7 (the
  `capabilities.yaml` schema) and Design 9 (stage ahead of artifacts).
- **Driving this item.** This item's implementation edits `tcw/`. From
  `implement` onwards, the repository's board is driven by editing files, per
  `CLAUDE.md`.
