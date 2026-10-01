# Spec — Core work model: stage table, item folders that never move, and advance

## Capability changes

**None in this slice.** This slice adds TCW 3.0's work model as a library: new
modules with tests, wired into no command. Nothing a user can run changes, so no
capability record changes. The records describing the 3.0 work axis (the work
lifecycle, `advance`, the `node`, `transition` and `definition-of-done` taxonomy
terms) change in the slices that ship the behavior: TCW-70 wires the model into
the CLI with the filesystem backend, and TCW-73 finishes the command surface.

Two existing records will need attention in those slices, and this spec names
them so they are not missed:

- `work/archive-a-resolved-item-before-it-is-deleted`, the ledger's one `work/`
  capability today. TCW-70 removes it, because 3.0 never deletes item folders.
- `capabilities/detect-capability-drift`. It promises that drift "never makes
  the capabilities axis depend on the work axis", and works by following each
  capability's `Planning doc` field. The 3.0 drift rule (Design 7) reads
  completed work items instead. TCW-73, which wires `capabilities drift`, rewrites
  that record; TCW-76 decides what happens to the `Planning doc` field.

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
3. **One move operation.** `advance` decides the target, checks the reason
   rules, runs the target stage's gates, moves the item together with its
   trace, and runs `post` hooks. It returns an outcome that maps onto TCW-73's
   exit codes.
4. **Two built-in gates that run during the lifecycle.** The records gate checks
   that the declared capability and taxonomy changes are in the records after
   implement. The completion gate checks that the verification rounds were
   accepted, and accepted for the latest implementation.
5. **A shared item-folder layout.** Item folders never move. Each stage's files
   sit in a stage folder: a revised document, or numbered rounds with
   verdicts, plus timestamped handoffs. Paths are computed in one place.
6. **An eight-operation backend interface** that both TCW-70 and TCW-71 can
   implement: create, read, list, update properties, set stage, comment,
   rename, and look up a backend name (such as a Jira key).
7. **The `work.*` configuration shape** is parsed and validated, and unknown or
   removed keys are errors.
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
   - everything Jira, including the Jira-only `tickets list` and
     `tickets adopt` commands, which work on tickets that have no item yet and
     so sit outside the backend interface: TCW-71.

  Tests use an in-memory backend that lives under `tests/`. It is not shipped.
- **Personal config and the `inherit` chain** (TCW-72). This slice parses the
  `prompt`, `pre`, `post` and `procedures` lists with today's `builtin: true`
  marker, and TCW-72 replaces that marker with `inherit`. TCW-72 also adds the
  layer that a failed `post` hook came from to `advance`'s outcome; this slice
  leaves room for it but does not fill it.
- **Renaming "node" to "project" across surviving code.** The new modules use
  "project" only, including the hook variable `TCW_PROJECT_ROOT`. The sweep
  through code that outlives 3.0 (the project registry, `tcw work nodes`, the
  `connected-projects` config keys, the `TCW_NODE_ROOT` variable) happens in
  TCW-73, which already touches every surface. TCW-73's ticket currently names
  only the command, so it must be widened to say this. Code that 3.0 deletes
  is not renamed first.
- **Prompts, skills, documentation and migration:** TCW-74, TCW-75 and TCW-76.
  This slice decides where built-in prompts live (Design 3) but writes none of
  their text.
- **The 2.x code.** None of it is changed or removed here. The two models
  coexist until TCW-70 switches over.

## Design

The new code lives in `tcw/work/` beside the 2.x modules, under names that do
not collide:

- `errors.py`: the exception classes, so that `model.py` and `backend.py` can
  both raise them without importing each other;
- `model.py`: identity, properties, the stage table;
- `config.py`: `work.*` parsing;
- `layout.py`: item-folder paths and round verdicts;
- `backend.py`: the backend protocol;
- `gates.py`: the built-in gates and drift;
- `advance.py`: the move operation;
- `references.py`: reference checks for `validate`.

Exit codes go in `tcw/exit.py` because all three axes use them.

### 1. Identity (`model.py`)

1. `Slug(project: str, folder: str)`. Its text form is `project/folder`.
   - `project` matches the project ID pattern (`tcw/store/project.py:22`,
     lowercase words joined by `-`). The 2.x reserved names
     (`RESERVED_PROJECT_IDS`, `project.py:23`) are **not** applied: they
     exist to keep project IDs apart from status-directory names, and 3.0 has
     no status directories. So `backlog/f` parses as project `backlog`, which
     is then an unknown project rather than a malformed slug.
   - `folder` matches `^[A-Za-z0-9][A-Za-z0-9-]*$`, at most 128 characters.
     Mixed case allows Jira keys such as `TCW-67-…`. Each backend narrows the
     pattern for the names it creates.
2. `Slug.parse(text, current_project)` accepts exactly two forms:
   - `project/folder`;
   - a bare `folder`, read as belonging to `current_project`.

   Anything else, including a nested path, is a usage error. A Jira key typed
   by a user is not a slug; the caller turns it into one through the backend's
   `lookup` operation (Design 5).
3. `title_words(title)` turns a title into the part of a folder name after
   its prefix: lowercase `[a-z0-9-]`, runs of other characters collapsed to
   one `-`, ends trimmed, cut at a `-` boundary to fit the length limit. A title
   with no letters or digits gives `untitled`. Each backend adds its own
   prefix. There is no `-2` suffix: a name that already exists is refused
   (exit 3).

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
   - an item that is its own parent or its own blocker is a usage error;
   - a `parent` that would make a cycle among this project's items (A's parent
     is B and B's parent is A, at any depth) is a usage error. Parents in
     other projects are not followed.
5. `blocks` is not stored. `blocks_of(item, items)` scans for items whose
   `blocked_by` names `item`. `edit --blocks X` becomes an update of X's
   `blocked_by`.
6. An item whose children are `list(parent=slug)` is an epic. There is no type
   flag and no depth limit in the model. A backend whose store limits depth
   (Jira's issue hierarchy) refuses a deeper child itself (TCW-71).

### 3. The stage table (`model.py`)

1. `STAGES` is a tuple of `Stage` records with these columns:
   - `name`;
   - `kind`: `flow`, `terminal` or `side`;
   - `artifact`: `document`, `rounds` or `none`;
   - `optional`: whether the stage can be disabled;
   - `verdict`: whether its rounds carry a verdict;
   - `on_reject`: the stage a rejected round sends the item back to;
   - `completion`: whether this is the stage finished work moves to;
   - `discard`: whether this is the stage abandoned work moves to;
   - `prompt`: whether TCW ships a built-in prompt for the stage;
   - `gates`: the names of its built-in gates.

   Order is tuple order.

| name | kind | artifact | optional | verdict | on_reject | completion | discard | prompt | gates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| inbox | flow | none | no | no | – | no | no | yes | – |
| request | flow | document | no | no | – | no | no | yes | – |
| spec | flow | document | yes | no | – | no | no | yes | – |
| plan | flow | document | yes | no | – | no | no | yes | – |
| implement | flow | rounds | no | no | – | no | no | yes | – |
| review | flow | rounds | yes | yes | implement | no | no | yes | – |
| qa | flow | rounds | yes | yes | implement | no | no | yes | – |
| completed | terminal | none | no | no | – | yes | no | no | completion |
| discarded | terminal | none | no | no | – | no | yes | no | – |
| postmortem | side | document | yes | no | – | no | no | yes | – |

2. **No other module contains a stage name as a literal**, either alone or
   inside a longer string such as a path. Behavior comes from the columns,
   not from names. Examples:
   - **The records gate** attaches to the stage that follows the last rounds
     stage without a verdict, which today is implement. That following stage
     is the next enabled flow stage; if no flow stage is enabled after it, the
     gate attaches to the completion stage.
   - **"Back to implement"** reads `on_reject`.
   - **The completion stage** and **the discard stage** are found by their
     columns. **[Decision]** These two columns replace "the first terminal
     stage" and a named `DISCARD` constant, so that the table, not its row
     order, says which stage is which.
   - **Where `new` starts** is the first flow stage whose artifact is not
     `none` (request). `new --stage inbox` names the first flow stage
     (inbox), which is allowed only when `backend.inbox_items` is true.
   - **Built-in prompts** are packaged files named by the stage's `name`
     column (`tcw/work/prompts/<name>.md`). TCW-74 writes their text; this
     slice only fixes where they are found.
3. **The enabled set** is the table minus the optional stages a project
   disabled.
4. **Side stages.** **[Decision]** A side stage is worked on, never moved
   into. It has a folder, a prompt and an artifact, and never changes an
   item's `stage`, as the ticket says. An agent works it with the stage's
   prompt and writes its document through `path`. `advance --to` a side stage
   is a usage error. This resolves the ticket's two statements "`--to` may
   name any stage" and "a side stage never changes an item's stage" in favour
   of the second. Because nothing moves into a side stage, its `pre` and
   `post` hooks could never run, so configuring them is an error (Design 8).
5. **[Decision] Rounds without a verdict.** Implement rounds carry no verdict:
   the ticket listed `round-N.md with a verdict` for all three loop stages,
   but an implementation round has nothing to accept. Only `verdict: yes`
   stages have verdicts.

### 4. Item-folder layout (`layout.py`)

1. The item folder is `<work path>/<folder>`. It is created by the backend's
   `create`, never moved by TCW, and never deleted by TCW.
2. Only stages whose artifact is not `none` get a folder: `<item>/<stage>/`.
   A disabled stage's folder is never created by TCW, and `path` refuses a
   disabled stage as a usage error.
3. A document stage's file is `<stage>/<stage>.md`.
4. **[Decision] Declared record changes** live at the item root:
   `<item>/capabilities.yaml`. The ticket put the file at
   `spec/capabilities.yaml`, but spec is optional; with spec disabled there
   would be no place to declare changes and the records gate would silently
   check nothing. The declaration belongs to the item, not to one stage.
   Whichever stage prompt is enabled first among spec, plan and implement
   tells the agent to write it (TCW-74).
5. A rounds stage's files are `<stage>/round-N.md`, where the name matches
   `^round-([1-9][0-9]*)\.md$`. Other files in the folder are not rounds and
   are ignored. `next_round(stage)` is one more than the highest existing `N`,
   or 1. Gaps are allowed, and the highest `N` is the latest round.
6. A round in a verdict stage starts with YAML front matter carrying two keys:

   ```yaml
   verdict: accepted        # or rejected
   judges: 3                # the latest round of the on_reject stage when this was written
   ```

   `judges` ties the verdict to the implementation it judged. It is the
   highest round number of the stage's `on_reject` stage at the time of
   writing, or 0 if that stage has no rounds.
7. `round_verdict(path)` returns `accepted`, `rejected` or `invalid`. `invalid`
   covers no front matter, a missing or unrecognised `verdict`, and a missing
   or non-integer `judges`.
8. `current_verdict(slug, stage)` is what the rest of the model reads. It
   returns:
   - `none` when the stage has no rounds;
   - `invalid` when the latest round is invalid;
   - `stale` when the latest round's `judges` is not the current highest
     round of the `on_reject` stage (the implementation changed after the
     verdict was written);
   - otherwise the latest round's `accepted` or `rejected`.

   Only `accepted` lets work go forward. This is what makes a review accepted
   before a qa rejection stop counting once the fix is written: the fix adds
   an implement round, and the old review round becomes `stale`.
9. Handoffs are `<stage>/handoff-<YYYYMMDDTHHMMSSZ>.md`, in UTC. The newest by
   name wins.
10. `path(slug, stage=None, *, next=False, handoff=False)` gives the item
    folder, the stage's document or folder, the next round's path (`next`),
    or a new handoff path for the current second (`handoff`). It never
    creates anything. A handoff path that already exists (two handoffs in one
    second) is refused (exit 3), so nothing is overwritten. This is the
    function behind `tcw work path` (TCW-70 wires the command).
11. **Concurrent writers.** `next_round` is computed, not reserved. Two agents
    on two branches can both write `round-3.md`; git reports that as a
    conflict when the branches meet, which is the correct place to settle
    it. TCW does not lock.
12. A stage whose record the backend keeps outside the folder has no files on
    disk: the request and qa in Jira mode. The backend declares this as
    `external_stages`, and `path` refuses such a stage (exit 3) with a message
    naming the backend.

### 5. Backend interface (`backend.py`)

```python
class WorkBackend(Protocol):
    project: str                          # tcw-config id
    external_stages: frozenset[str]       # stages whose record lives in the backend
    inbox_items: bool                     # may an item sit at the inbox stage?

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None) -> Item: ...
    def read(self, folder: str) -> Item: ...
    def list(self, query: Query) -> list[Item]: ...
    def update(self, folder: str, changes: Changes) -> Item: ...
    def set_stage(self, folder: str, stage: str, note: str | None) -> str | None: ...
    def comment(self, folder: str, text: str) -> None: ...
    def rename(self, folder: str, title_words: str) -> Item: ...
    def lookup(self, name: str) -> str | None: ...
```

1. `Query` fields are:
   - `stages`: a set of stage names, or `None` for the default;
   - `parent`;
   - `assignee`;
   - `all`: include every item whatever its stage.

   The default (`stages=None`, `all=False`) is every item at a non-terminal
   stage **and every item with no stage**, so that a Jira ticket in an
   unmapped status, which needs attention, is not hidden. `stages` and `all`
   together are a usage error.
2. `set_stage(folder, stage, note)` moves the item and, when `note` is given,
   records the note as a comment **as part of the same move** where the store
   allows it (Jira: one transition request carrying the comment; filesystem:
   write the stage, then the comment file). It returns the stage the backend
   reports after the move (Jira re-reads the status). It raises:
   - `Refused` when the backend cannot make this move (Jira: no single
     transition offered to the target's status), having changed nothing;
   - `MovedWithoutNote` when the stage changed but the note could not be
     recorded.

   It runs no checks and no hooks; that is `advance`'s job.
3. `lookup(name)` turns a backend-specific name into a folder, or `None`.
   The filesystem backend always returns `None`. The Jira backend accepts an
   issue key and returns the folder whose name is that key followed by `-`.
   This is an exact match on the key, which TCW-71 makes authoritative in the
   folder name; it is not prefix matching of slugs, which TCW-73 forbids.
   **[Decision]** This is the eighth operation; the ticket listed seven, but
   TCW-73's slug input accepts a Jira key and nothing else could resolve it.
4. Errors are exception classes in `errors.py`, each carrying an exit code:
   - `UsageError` (2);
   - `Refused` (3);
   - `NotFound` (4);
   - `Unreachable` (5);
   - `MovedWithoutNote` (6);
   - `BackendError` (1).
5. Each operation is atomic as far as the backend allows, and changes only
   what it names. `create` makes the folder.
6. **Not in the interface:**
   - layout, paths and artifacts, which are shared files;
   - Jira-only ticket commands (`tickets list`, `tickets adopt`), TCW-71;
   - DoD, graveyard, retention, claims, plan stages, sidecars, the inbox
     verbs and tracker sync, all of which 3.0 removes.

### 6. Moving: `advance` (`advance.py`)

`advance(backend, config, slug, to=None, force=False, reason=None, dry_run=False) -> Outcome`
runs these steps in order. **Usage errors (2) and not-found (4) are raised;
every other result, including refusals, is returned as an `Outcome`** whose
`code` is the exit code. Errors the backend raises other than `Refused` and
`MovedWithoutNote` (for example `Unreachable`) propagate with their own code.

1. **Usage checks** (raise `UsageError`; nothing is read or written):
   - `force` without a non-empty `reason`;
   - a `to` that is not in the table, is disabled, or is a side stage;
   - a `to` naming the discard stage without a non-empty `reason`.
2. **Read** the item. A missing item raises `NotFound`.
3. **Choose the target.**
   - A given `to` is the target.
   - With no `to`, the target depends on the current stage:
     - no stage: refused (exit 3);
     - a terminal stage: refused (exit 3);
     - a verdict stage in `backend.external_stages`: refused (exit 3) with a
       message saying to name the target with `--to`, because the verdict
       lives in the backend and the model cannot read it;
     - any other verdict stage: by `current_verdict` (Design 4.8):
       `rejected` targets that stage's `on_reject`; `accepted` targets the
       next enabled flow stage, or the completion stage if there is none;
       `none`, `invalid` and `stale` are refused (exit 3) with a message
       naming the round file to write;
     - otherwise: the next enabled flow stage, or the completion stage if
       there is none.
   - A target equal to the current stage is refused (exit 3) as a no-op.
   - A target that is the inbox stage is refused (exit 3) when
     `backend.inbox_items` is false. In Jira mode an inbox entry is a ticket
     without an item, so an item can never be at inbox.
4. **Check direction and reasons.** Each of these is refused (exit 3) unless
   its condition is met:
   - **Skips** need `force`. A move to a later stage that passes at least one
     enabled flow stage between the current stage and the target is a skip.
     The completion stage counts as later than every flow stage: moving from
     spec to completed with plan and implement enabled is a skip. Moving back
     is never a skip. Moving to the discard stage is never a skip.
   - **Leaving a verdict stage forward** (to any later stage other than the
     discard stage) needs `force` unless the stage is external or its
     `current_verdict` is `accepted`. This stops `--to qa` from a rejected
     review.
   - **Moving from no stage** needs `force`, because there is nothing to
     measure a skip from. **[Decision]** The exception is the discard stage,
     which needs only its reason, so an item in an unmapped Jira status can be
     discarded without forcing.
   - **Leaving a terminal stage** (reopening a completed or discarded item)
     needs a `reason`. It is a backward move, so it needs no `force`.
   - **Leaving an external verdict stage** needs a `reason`. This is how a
     Jira qa rejection is recorded: `advance --to implement --reason "…"`
     (TCW-71 requires a comment on a rejection), and acceptance is
     `advance --to completed --reason "…"`.

   A `reason` given on any other move is accepted and recorded.
5. **Gates.** These run only for the target, built-in gates first, then its
   configured `pre` bindings whose `when:` matches the item (Design 8). Hooks
   run with these environment variables added to the caller's environment:
   `TCW_SLUG`, `TCW_STAGE` (the target), `TCW_FROM_STAGE` (empty when there is
   none), `TCW_ITEM_PATH`, `TCW_PROJECT_ROOT`, and `TCW_FORCED` and
   `TCW_REASON` when forced. Each hook runs under the configured timeout
   (`work.hooks.timeout`).
   - Without `force`, gates run in order and stop at the first failure, which
     refuses the move (exit 3).
   - With `force`, every gate runs and every failure is collected. Each is
     reported on stderr and the move continues.
6. **Dry run** stops here. It returns the would-be outcome: OK when the move
   would happen, and the refusal otherwise. **It answers only for the model's
   checks.** It does not ask the backend whether it can make the move, so in
   Jira mode a dry run can say OK for a transition the workflow does not
   offer. `tcw validate --remote` (TCW-71) is where workflow problems are
   found ahead of time.
7. **Move** with `backend.set_stage(folder, target, note)`. `note` is the
   trace, given whenever the move has a `reason`. It names the source and
   target stages, says whether the move was forced, gives the reason, and
   lists every gate failure that was overridden.
   - `Refused` from the backend: nothing moved, nothing is recorded, `post`
     does not run, and the outcome is exit 3. `pre` hooks have already run, so
     they must be safe to run again; this is stated in the hook documentation
     (TCW-75).
   - `MovedWithoutNote`: the move stands. The outcome will be exit 6 with a
     message saying the trace was not recorded, so the caller can add it with
     `tcw work comment`. `post` still runs.
   - A reported stage different from the target: the outcome is exit 1,
     naming both stages, and `post` does not run.
8. **`post` bindings** run, under the same environment and timeout. A failure
   keeps the move and gives exit 6.
9. **Result.** The outcome carries the code, the stage the backend reported,
   any messages, and the overridden gate failures. TCW-73 prints the stage on
   stdout.

**[Decision] Exit 6** means "the item moved, but something after the move
failed": a `post` hook, or the trace. TCW-73's table today says only "a post
hook failed"; it must be widened to match.

Creating an item (`new`, adopt, delegation) is not a move and runs no gates.
`new` starts at the first flow stage with an artifact (request), or at inbox
with `--stage inbox` when `backend.inbox_items` is true.

`discard(backend, config, slug, reason)` is `advance(..., to=<discard stage>,
reason=reason)`.

### 7. Built-in gates (`gates.py`)

**The declaration file.** `<item>/capabilities.yaml` (Design 4.4). The schema
is:

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
`added:` alias goes (it is accepted today at `base.py:364-400`). A missing
file declares nothing.

**The records reader.** The gate does not open ledgers itself. It asks a
`RecordsReader`, which answers three questions. Each answer can also be
**unchecked, with a reason**, when the reader could not find out (an
unreachable or unledgered child project, an ambiguous reference, an
unreadable ledger or `meta.yaml`). The gate treats unchecked as a failure.

- `capability(path)`: `absent`, or `present` with its status.
- `removal(path)`: `removed` (no local capability at the path), `still-local`
  (a local capability is still there), or `inherited` (the path names a
  capability inherited from an extended ledger, which no local removal can
  satisfy). This mirrors today's rule (`recursion.py:126-146`): after a local
  capability is removed, its path may fall through to an inherited one at the
  same path, and that counts as removed.
- `term(term)`: `absent` or `present`, through this project's taxonomy as
  `tcw taxonomy` resolves it.

Paths are routed to the ledger that answers for them by today's rule
(`route_capability_path`, `recursion.py:204-253`). Its routing failures become
unchecked answers. The production reader is filesystem-specific, because the
capabilities store is (`get_local` and `extends` exist only on
`FsCapabilitiesStore`); the gate depends only on the reader protocol.

**The records gate.** It fails when the declaration file is unreadable or
malformed, or when any declared change is not in the records:

- each `new` or `changed` path is `present`;
- each `new` path does not have status `Missing`;
- each `removed` path answers `removed`;
- each `new` or `changed` term is `present`;
- each `removed` term is `absent`.

It replaces `capability_gate` (`recursion.py:50-165`) and its planned-`Missing`
assumption.

**The mid-work check.** `records_problems(..., finished=False)` runs the same
reading but reports only what is wrong at any point in the work: an unreadable
or malformed file, an unknown key, an unchecked answer, and an `inherited`
removal. It does not report changes that are simply not made yet. This
replaces today's `capability_gate(in_progress=True)` call in `tcw validate`
(`tcw/validate.py:268-295`); TCW-73 wires it in.

**The completion gate.** For each enabled verdict stage that is not in
`backend.external_stages`, `current_verdict` must be `accepted`. `none`,
`invalid` and `stale` fail. In Jira mode the qa verdict is the status move
itself, so only review is checked there; with review also disabled, the gate
checks nothing in Jira mode.

**Drift.** `drift_problems(items)` takes completed items and re-checks their
declarations against the records today.

- For each declared path or term, the **latest** declaration wins: the one
  from the completed item with the newest `created` date. A later item that
  declares the same path differently supersedes an earlier one, which is
  how a drift report is cleared.
- If the newest declarations disagree (two items created the same day, one
  saying `new` and one `removed`), the path is reported as **ambiguous**,
  not as drift and not silently.
- A latest `new` or `changed` path that is now `absent` is drift. A latest
  `new` path that is now `Missing` is drift. (`changed` paths are not checked
  for `Missing`, matching the gate.)
- A latest `removed` path that no longer answers `removed` is drift.
- Terms follow the same rules.
- An unchecked answer is reported as unchecked.

This replaces `_shipped_but_missing` (`tcw/capabilities/cli.py:200-254`), which
follows `Planning doc` fields instead. Items completed before 3.0 kept no
declaration file in a folder (most are now graveyard records), so 3.0 drift
does not cover them; see Capability changes. TCW-73 wires it into
`capabilities drift`.

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
- `hooks`;
- `jira`, passed on unparsed to TCW-71's backend, and an error when `backend`
  is not `jira`.

`work.hooks` takes **[Decision]** `timeout` (seconds, a positive number,
default 300) and `output-cap` (bytes, a positive integer, default 65536).
They replace `work.lifecycle.timeout` and `work.lifecycle.output-cap`
(`base.py:2982-2999`), which hook commands and `generate:` prompt bindings
still need.

Each `work.stages.<stage>` takes:

- `enabled`: refused on a stage whose `optional` is no;
- `status`: a non-empty string, accepted only when `backend` is `jira`;
- `prompt`;
- `pre`;
- `post`.

The binding lists:

- `prompt` takes `blob`, `file`, `generate`, `builtin` and `skill` bindings,
  as today.
- `pre` takes `command` bindings only. **[Decision]** A `skill` in `pre` is an
  error, because TCW cannot run a skill and a gate that is only reported
  would always pass.
- `post` takes `command` and `skill` bindings; a skill is reported, not run.
- `when:` takes `tags` and `not_tags`, spelled as today. **[Decision]** `when: {type: …}` is an
  error, because 3.0 items have no type.

The checks:

1. An unknown stage name is an error.
2. A stage key outside the five above is an error.
3. A side stage accepts only `enabled` and `prompt`; `pre`, `post` and
   `status` on it are errors, because nothing ever moves into it.
4. The removed 2.x keys are errors that name the migration guide
   (`docs/migration-guide-2.X-to-3.0.0.md`, the name TCW-76 uses):
   - `work.lifecycle`, including its `artifacts` templates. **[Decision]**
     A per-tag document template becomes a `file` binding with a `when:`
     condition in that stage's `prompt` list. This repository's `spec-bug.md`
     template (`tcw-config.yaml:104-110`) moves that way in TCW-76;
   - `work.tracker`;
   - `work.auto-commit-transitions`;
   - `work.publish-transitions`;
   - `work.trunk-branch`;
   - `work.retain`.
5. Any other unknown key under `work`, `work.hooks` or a binding is an error.
6. With `backend: jira`, every enabled stage except side stages must have a
   `status`, and no two enabled stages may share one. This includes inbox,
   because delegation puts new tickets in the inbox status (TCW-71).

### 9. References (`references.py`)

`reference_problems(items, resolve)` checks every `parent` and `blocked-by`
entry. The caller passes **every** item, finished ones included (`Query(all=True)`),
or every reference to a completed blocker would look missing.

- A slug in this project that does not exist is a **warning**: "references a
  missing item".
- A slug in another project goes through `resolve`, which answers `found`,
  `missing` or `unresolved`. `unresolved` means the project cannot be reached
  from here. It is printed as its own line, "unresolved", and is neither a
  warning nor an error.

In Jira mode `parent` and `blocked-by` live in Jira, so this check runs under
`validate --remote`.

**[Decision on the open question] Stage ahead of artifacts.** `stage_problems`
checks each item at a **non-terminal flow stage**; items with no stage and
finished items are skipped. Any enabled document or rounds stage before the
item's stage that is not external and has no artifact is a **warning**. A
forced skip therefore warns until the item finishes; the warning text says
so. It applies in both modes; in Jira mode it runs under `validate --remote`,
because reading the stage needs the network.

### 10. Git

None of the new modules imports `subprocess`, `os.system`, `os.popen`, or the
git helpers in `tcw/store/fs.py`. Hooks are run through the shared hook
runner. The new modules write only the files they name.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| create, read, list, update, set stage, comment, rename, lookup | **Backend interface.** Jira implements each one: issue create, get, JQL, edit, transition with an optional comment, comment, a local folder rename plus a TCW Item field update, and a key-to-folder match. |
| `advance`, gates, `discard` | **Model.** Built only on the interface, the layout and the records reader. |
| Item-folder layout, rounds, handoffs, `path` | **Shared layout**, not an interface operation. Git owns technical artifacts in both modes, so the files exist in both. |
| `external_stages`, `inbox_items` | **Backend facts.** These are declared, not detected. |
| Records gate, drift | **Model** over the `RecordsReader` protocol. The production reader is filesystem-only, as the capabilities store is today; a second capabilities store would supply its own reader. |
| `blocks` | **Derived by query.** Nothing stores it. |

**What 3.0 changes about the litmus test.** The model now reads item folders
in both modes, because the technical record is files in git whichever backend
owns status. `docs/lifecycle/abstraction.md` still describes stores that keep
everything elsewhere, folder moves as transitions, and "node" vocabulary. Its
rewrite belongs to TCW-75.

## Acceptance criteria

All criteria are checked by pytest tests in `tests/work/`, against the in-memory
backend (`tests/work/memory_backend.py`) and temporary directories. Unless a
criterion names a helper, it is checked **through `advance`** (or `discard`).

1. **Identity.**
   - `Slug.parse` accepts `p/f` and a bare `f`.
   - It rejects `a/b/c`, an empty value, a folder with `_` or spaces, a
     project with uppercase letters, and a folder longer than 128 characters.
   - `Slug.parse("backlog/f", "tcw")` is project `backlog`, folder `f`.
   - `str(Slug.parse("tcw/TCW-67-x", "tcw")) == "tcw/TCW-67-x"`.
2. **Title words.**
   - `title_words("Make tcw validate usable: a gate!") == "make-tcw-validate-usable-a-gate"`.
   - `title_words("!!!") == "untitled"`.
   - The output is at most the folder limit minus a 20-character prefix
     allowance, and does not end in `-`.
3. **Properties.** Each of these is a `UsageError`:
   - a priority outside the five names (including an integer);
   - effort `huge`;
   - a tag not registered;
   - a free-text blocker;
   - an item set as its own parent or its own blocker;
   - A's parent set to B when B's parent is A.
4. **Blocks are derived.** After `edit --blocks` semantics (updating B's
   `blocked_by` with A), `blocks_of(A)` returns `[B]`, and A's own record is
   unchanged.
5. **No literal stage names.** A test scans `tcw/work/{errors,advance,gates,
   layout,backend,references,config}.py` and `tcw/exit.py`. No string constant
   in them contains a stage name as a whole word (so `"spec/capabilities.yaml"`
   fails and `"specification"` passes), docstrings excepted. In `model.py`,
   stage names appear only inside `STAGES`.
6. **Disabling stages.**
   - With review and qa disabled, a bare `advance` from implement moves to
     completed, and the records gate runs on that move.
   - With plan disabled, a bare `advance` from spec moves to implement.
   - Disabling `implement` or `request` is a config error.
7. **Bare advance.**
   - It goes from request to spec.
   - From review whose current verdict is `rejected`, it goes to implement.
   - From review whose current verdict is `accepted` (qa enabled), it goes
     to qa.
   - From review with no round, with an `invalid` round, and with a `stale`
     round, it is refused (exit 3) and the message names the round file.
   - After review round 1 (`judges: 1`) is accepted and implement round 2 is
     written, a bare advance from review is refused as `stale`.
   - From qa whose current verdict is `rejected`, it goes to implement.
   - From qa with `external_stages = {request, qa}`, it is refused (exit 3)
     and says to use `--to`.
   - From a terminal stage, and from no stage, it is refused (exit 3).
   - On an unknown slug it raises `NotFound`.
8. **Skips, reasons and backward moves.**
   - `--to implement` from spec (plan enabled) is refused without force.
   - `--to completed` from spec, with review and qa disabled, is refused
     without force.
   - With `force` and a reason, it moves, and the `set_stage` call carries a
     note containing the reason.
   - `--to spec` from review moves without force, and `set_stage` gets no
     note.
   - `--to qa` from review with a rejected current verdict is refused
     without force.
   - `--to discarded` without a reason raises `UsageError` and the backend
     records no call; with a reason it moves from any stage, including no
     stage without force, and the note carries the reason.
   - `--to implement` from completed without a reason is refused; with a
     reason it moves and the note carries it.
   - With `external_stages = {request, qa}`, `--to implement` from qa
     without a reason is refused; with one it moves with a note.
   - `--to inbox` from request is refused when `inbox_items` is false.
   - `--to postmortem` is a `UsageError`.
   - `force` with no reason is a `UsageError`, and the backend records no
     call.
9. **Gates run for the target only.**
   - A failing `pre` on review refuses a move into review (exit 3), and the
     backend's stage is unchanged.
   - A failing `pre` on spec does not affect a move from spec to plan.
   - With `force` and two failing `pre` hooks, both run, the move happens,
     and the note names both.
   - A `pre` hook whose `when:` tags do not match the item does not run.
   - A hook that is not a shell builtin (`python -c …`) runs, and a hook
     asserting `TCW_STAGE`, `TCW_FROM_STAGE`, `TCW_ITEM_PATH` and
     `TCW_PROJECT_ROOT` passes.
   - The records gate refuses a move into review when a declared `new` path
     does not resolve.
   - The completion gate refuses a bare advance into completed when review's
     current verdict is not `accepted`.
10. **Post hooks and the trace.**
    - A failing `post` returns exit 6, and the backend's stage is the target.
    - A backend whose `set_stage` raises `MovedWithoutNote` on a forced move
      gives exit 6, a message naming the missing trace, and `post` still runs.
    - A backend whose `set_stage` raises `Refused` gives exit 3, no stage
      change, and `post` does not run.
11. **Dry run.** It runs the gates and returns the would-be outcome. The
    backend records no `set_stage` and no `comment` call.
12. **Missing stage.** An item whose backend stage is `None` is moved by
    `--to spec --force --reason r` and refused without `force`.
13. **Records gate.** Through the gate function with a fake reader, each of
    these is a failure:
    - a `new` path that is `absent`;
    - a `new` path with status `Missing`;
    - a `changed` path that is `absent`;
    - a `removed` path that answers `still-local`, and one that answers
      `inherited`;
    - a `taxonomy.new` term that is absent, and a `taxonomy.removed` term
      that is present;
    - any answer that is unchecked;
    - an unknown key;
    - unreadable YAML.

    A missing file passes. A `removed` path that answers `removed` passes.
    `records_gate_stage` is review, then completed when review and qa are
    disabled. The mid-work check reports an `inherited` removal but not a
    `new` path that is still `absent`. One test builds the production reader
    over a real temporary `FsCapabilitiesStore` and checks a local path's
    `Missing` status and a local `removed` path.
14. **Completion gate.** Through the gate function, each of these fails:
    - no review round;
    - latest review round `invalid`;
    - latest review round `stale`;
    - review accepted but qa's current verdict `rejected`.

    With `external_stages = {request, qa}`, only review is checked.
15. **Layout.**
    - `path(slug, "review", next=True)` is `round-3.md` when rounds 1 and 2
      exist, `round-6.md` when rounds 1 and 5 exist, and `round-1.md` when
      none do.
    - `round-01.md`, `Round-2.md` and `round-3-draft.md` are not rounds.
    - Handoff names match `handoff-\d{8}T\d{6}Z\.md`, the newest by name is
      the latest, and a handoff path that already exists is refused.
    - `path` for an external stage, and for a stage whose artifact is
      `none`, is `Refused`; for a disabled stage it is a `UsageError`.
    - `path` creates nothing on disk.
16. **Config.**
    - Each removed 2.x key is an error naming the migration guide.
    - An unknown `work.*` key, and an unknown `work.hooks` key, is an error.
    - An unknown stage, or an unknown key on a stage, is an error.
    - `pre` or `post` on postmortem is an error.
    - A `skill` binding in `pre`, and `when: {type: epic}`, are errors.
    - `status` or `jira:` with `backend: filesystem` is an error.
    - Two enabled stages with one `status` in Jira mode is an error, and a
      missing `status` on inbox in Jira mode is an error.
    - `work.hooks.timeout: 0` is an error; an absent `hooks` gives 300 and
      65536.
    - A fixture copy of this repository's current `tcw-config.yaml` reports
      `lifecycle`, `tracker` and `retain` as removed. The fixture is a copy,
      so migrating the real file (TCW-76) does not break the test.
17. **References.**
    - A missing same-project `blocked-by` is a warning.
    - A `blocked-by` naming a completed item is not a warning.
    - A cross-project ref whose project cannot be resolved is reported as
      unresolved and not as a warning.
    - An item at `plan` with no `spec/spec.md` (spec enabled) gets the
      stage-ahead warning. With spec disabled, it does not. A discarded item
      with no artifacts gets none.
18. **Drift.**
    - A completed item declaring `new: [x/y]` while `x/y` is absent is drift.
    - If a completed item created later declares `removed: [x/y]`, it is not.
    - If a completed item created earlier declares `removed: [x/y]`, it still
      is.
    - Two items created the same day declaring `x/y` both ways report it as
      ambiguous.
    - A latest `changed: [x/y]` while `x/y` is `Missing` is not drift.
19. **No git.** A test asserts that none of the new modules imports
    `subprocess` or calls `os.system` or `os.popen`, except the hook runner
    they call, and that none references the git helper names in
    `tcw/store/fs.py`. A second test runs a forced `advance` with hooks inside
    a temporary git repository and asserts that `git rev-parse HEAD`,
    `git status --porcelain` and `git for-each-ref` are unchanged.
20. **2.x untouched.** The full existing test suite passes unchanged.

### Coverage

| Design rule | Criteria |
| --- | --- |
| 1 Identity | 1, 2 |
| 2 Properties | 3, 4 |
| 3 Stage table | 5, 6, 8 (side stage, discard column) |
| 4 Layout, verdicts | 7 (stale), 14, 15 |
| 5 Backend interface | 8, 10 (`set_stage` note and errors), 7–14 through the memory backend. Atomicity is per backend; TCW-70 and TCW-71 own it. `lookup` is exercised by TCW-71. |
| 6.1 Usage | 8 |
| 6.2 Read | 7 (`NotFound`), 12 |
| 6.3 Target | 7, 8 (inbox) |
| 6.4 Direction and reasons | 8, 12 |
| 6.5 Gates | 9 |
| 6.6 Dry run | 11 |
| 6.7 Move and trace | 8, 10 |
| 6.8 Post | 10 |
| 7 Gates, drift | 9, 13, 14, 18 |
| 8 Config | 6, 16 |
| 9 References | 17 |
| 10 Git | 19 |

## Risks

- **Two models coexist until TCW-70.** The new code is unused in production
  until then, so a design mistake may surface late. Mitigation: the memory
  backend exercises every path, and before implementation the backend
  interface is read against TCW-70's and TCW-71's tickets, listing any
  operation either would have to fake (done once in review; see Notes).
- **The column-driven stage rules are subtle.** A future custom stage could
  make them read wrongly. Mitigation: `completion` and `discard` are explicit
  columns rather than positions, criterion 5 forbids name literals, and
  criteria 6, 9 and 13 pin the rules under disabled stages.
- **`judges` must be written correctly.** A verdict with the wrong `judges`
  number is `stale` and blocks the item until rewritten. That is the safe
  direction: it can delay work, never let unreviewed work through. The review
  and qa prompts (TCW-74) get the number from `path` output.
- **Records-gate timing.** Running at the stage after implement means an item
  forced past review skips the records check. That is accepted: forcing is
  deliberate and leaves a note listing what was overridden.
- **`pre` hooks run before a backend refusal.** In Jira mode a transition the
  workflow does not offer is found only at the move, after `pre` hooks ran.
  Mitigation: hooks must be safe to re-run, and `validate --remote` checks
  the workflow ahead of time.
- **Drift by creation date.** Two items created the same day that disagree
  cannot be ordered; they are reported as ambiguous rather than guessed.
- **A trace that fails after a move** leaves a move with no note. The backend
  records the note in the same request where it can, and otherwise exit 6
  and the message tell the caller to add it with `tcw work comment`.

## Notes

- **Decisions made in this spec, confirmed by the owner on 2026-10-01.** Each is marked
  **[Decision]** in the design:
  - the model lands as a library and TCW-70 wires it in;
  - implement rounds carry no verdict;
  - verdicts carry `judges`, and a verdict about an older implementation is
    `stale`;
  - `completion` and `discard` are table columns;
  - side stages are worked, never moved into, and take no `pre` or `post`;
  - built-in prompts are packaged files named by stage;
  - `capabilities.yaml` lives at the item root, not under `spec/` (the
    ticket and TCW-73's ticket say `spec/capabilities.yaml`; both need
    updating);
  - `lookup` is an eighth backend operation;
  - `set_stage` records the trace note as part of the move and returns the
    reported stage;
  - exit 6 also covers a missing trace (TCW-73's table needs widening);
  - discard, reopening a finished item and leaving an external verdict stage
    require a reason; discarding needs no force even from no stage;
  - `work.hooks.timeout` and `work.hooks.output-cap` replace the
    `work.lifecycle` limits;
  - `artifacts` templates become conditional `prompt` bindings;
  - `skill` bindings are refused in `pre`, and `when.type` is refused;
  - drift judges each path by its newest declaration, and reports same-day
    disagreements as ambiguous;
  - "stage ahead of artifacts" is a warning in both modes, for unfinished
    items only;
  - the "node" sweep, including config keys and `TCW_NODE_ROOT`, goes to
    TCW-73 (its ticket needs widening).
- **Changes other tickets need.** TCW-73: exit 6's meaning, the "node" sweep
  scope, `capabilities drift` reading `<item>/capabilities.yaml`, and the
  `detect-capability-drift` record. TCW-71: `set_stage` with a note and a
  reported stage, `lookup`, the qa reason rules. TCW-72: the failed `post`
  hook's layer in the outcome. TCW-76: the hook variable renames
  (`TCW_STATUS`, `TCW_TRANSITION`, `TCW_NODE_ROOT` and `TCW_RESOLUTION` become
  `TCW_STAGE`, `TCW_FROM_STAGE` and `TCW_PROJECT_ROOT`, and the resolution
  goes), the `artifacts` move, and `Planning doc`. Nothing has been posted to
  those tickets.
- **The ticket's open questions** are answered in Design 7 (the
  `capabilities.yaml` schema) and Design 9 (stage ahead of artifacts).
- **Review.** A multi review on 2026-10-01 (four Claude reviewers and the
  local model; Codex was out of quota) found that the first version of this
  spec let a missing or stale verdict pass, could not express a Jira qa
  rejection, checked the discard reason after the move, returned "not moved"
  exit codes after a move, reused 2.x hook code that does not fit 3.0 items,
  and tied the records gate to the optional spec stage. This version
  addresses each. The owner confirmed every **[Decision]** above on
  2026-10-01, and `plan.md` was rewritten against this version.
- **Driving this item.** This item's implementation edits `tcw/`. From
  `implement` onwards, the repository's board is driven by editing files, per
  `CLAUDE.md`.
