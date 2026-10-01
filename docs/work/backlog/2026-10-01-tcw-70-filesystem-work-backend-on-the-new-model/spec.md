# Spec — Filesystem work backend on the new model, wired into `tcw work`

## Capability changes

This is the slice where TCW 3.0's work axis becomes something a user can run, so
it changes the capability ledger more than any other slice. The rule applied
below: **a record changes in the slice whose code changes the behavior it
describes** (TCW-75's ticket states this rule for every slice). Every record under
`docs/capabilities/work/` was read; there are 46. The epic's decision 12 makes
this slice decide each of the 46, because it removes the 2.x store they
describe. TCW-71 writes its own Jira-mode records, and TCW-73 changes command
wording in surviving records afterwards.

All deltas below are planned. No record is written at this stage.

### Capability records

**Removed (23).** Each describes behavior that exists only in the 2.x work store
or the 2.x tracker integration, both of which this slice deletes. Jira-mode
records come back with TCW-71, written for its own model.

| Record (`work/…`) | Why it goes |
| --- | --- |
| `archive-a-resolved-item-before-it-is-deleted`, `keep-resolved-work-out-of-git` | Retention: 3.0 never deletes an item folder and writes no ignore rules. |
| `customize-the-definition-of-done` | `dod.yaml` goes; a project gates completion with its own `pre` hooks. |
| `record-a-tombstone-for-resolved-work` | `graveyard.yaml` and `tombstone add` go. |
| `drop-a-work-item` | Hard delete goes; TCW never deletes an item folder. |
| `start-a-work-item`, `submit-a-work-item-for-review`, `rework-a-reviewed-work-item`, `complete-a-work-item` | Replaced by `advance` (new record below). |
| `reconcile-an-epic-rollup`, `coordinate-a-cross-node-epic` | `reconcile`, `--epic` and `--initiative` go; an item with children is an epic (changed `decompose-a-work-item-into-children`). |
| `delegate-a-request-to-a-child-node`, `escalate-a-request-to-the-parent-node` | Replaced by `new --project` (new record below). |
| `capture-raw-intake` | `intake.md` goes; piped text becomes the request document (changed `open-a-work-item`). |
| `customize-lifecycle-artifact-templates` | `scaffold` and `work.lifecycle.artifacts` go; a template becomes a `file` binding in a stage's `prompt` list (changed `configure-the-work-lifecycle`). |
| `publish-store-writes-to-the-remote` | TCW never pulls or pushes. |
| `share-a-work-store-between-sessions` | The store lock and per-command commits go (Design 4.6). |
| `hold-a-tracker-ticket`, `inherit-tracker-settings-from-parent-nodes`, `inspect-external-tracker-work`, `manage-external-tracker-intake`, `require-tracker-backed-work`, `synchronize-external-tracker-work` | The 2.x tracker integration goes (Design 9). |

**New (3).**

| Record | What it says |
| --- | --- |
| `work/advance-a-work-item` | `tcw work advance <slug> [--to] [--force --reason] [--dry-run]`: the one move command, its gates, reasons and exit codes, as TCW-69 defines them. |
| `work/comment-on-a-work-item` | `tcw work comment <slug>` reads text from stdin and records it; in filesystem mode it is a file under `comments/`. Forced moves and discards leave their reason the same way. || `work/delegate-a-work-item-to-another-project` | `tcw work new --project <id>` and `edit --blocks` into another filesystem-mode project, its three conditions, the inbox landing, and files left uncommitted. Replaces the two removed delegation records; a new path because the old ones say "child" and "parent". |

**Changed (28).** Twenty under `work/`, each because its text names a command,
file or behavior that changes here:

- `configure-the-work-lifecycle` (`work.lifecycle` becomes `work.stages` and
  `work.hooks`);
- `run-a-lifecycle-stage` (`stage gate` and `stage validate` go; `stage prompt`
  stays);
- `inspect-the-lifecycle-contract` (the stage table instead of stages and
  transitions);
- `read-the-documentation-gate-for-a-change` (names `stage gate`);
- `run-a-procedure` (names the backlog);
- `configure-the-work-store-location` and
  `declare-the-work-stores-home-repository` (name commits and transitions);
- `declare-capability-changes-in-a-child-nodes-ledger` (the file moves to the
  item root and is checked by the records gate after implement, not at
  completion);
- `decompose-a-work-item-into-children` (no status folders; `list --parent`);
- `discard-a-work-item` (`tcw work discard <slug> --reason`);
- `estimate-a-work-items-effort-and-complexity` (the `L/M/H/VH` shorthand goes);
- `manage-blocking-relations` (`item.yaml`; blockers are always items; only
  parent cycles are refused);
- `manage-the-work-inbox` (inbox-stage items);
- `open-a-work-item` (folder name, `request/request.md`, `--stage inbox`, named
  priority, no `-2` suffix);
- `prioritize-a-work-item` (named scale);
- `read-a-work-item` (`show`, `show --json`, `path <slug> [<stage>]`);
- `rename-a-work-item` (Design 5);
- `retitle-a-work-item` (names `initial-request.md`);
- `tag-a-work-item` (names `state.yaml`; `list --tag` stays, filtering on
  `item.yaml` tags, the owner's answer of 2026-10-01);
- `view-the-board` (`list` flags, `--tag` kept; no status columns, no
  descendant boards).

Eight elsewhere:

- `cli/locate-tcw-storage-folders` (`tcw work inbox path` goes);
- `cli/reference-a-tcw-object` (no resolved-item records);
- `cli/validate-a-node` (the work checks of Design 10);
- `cli/provision-declared-stores` (no publishing after a move);
- `cli/scaffold-the-doc-trees` (the work skeleton of Design 11);
- `cli/get-a-suggestion-for-a-mistyped-command` (its examples name removed
  commands);
- `capabilities/detect-capability-drift` (Design 10.3; the epic's decision 2
  gives this rewrite to this slice);
- `web/editing` (work items are no longer editable in `tcw serve` until TCW-77;
  Design 12).

**Unchanged (3):** `work/configure-procedures`,
`work/declare-which-documents-track-which-changes`, and
`work/inspect-the-node-topology`, which TCW-73 renames.

### Taxonomy

- **New Vocabulary** under `work-item/`: `round` (a numbered document of a stage
  that loops, carrying a verdict where the stage has one), `handoff` (a
  timestamped note for whoever resumes a stage), and `comment` (a dated remark
  on an item, kept by the backend).
- **Changed:**
  - `work-item` ("moves through a status state machine" becomes "moves through
    the stages of the stage table");
  - `work-item/transition` ("an atomic move between status folders" becomes "a
    change of stage made by `advance` and recorded by the backend");
  - `work-item/lifecycle-stage` and `work-item/lifecycle-hook` (the stage table;
    no artifact-template role);
  - the features `work-inbox` and `configurable-work-lifecycle`;
  - the skill features `configure-skill`, `extras-triage-issues-skill`,
    `commands-process-inbox-skill` and `work-create-skill`, **only** to drop
    their references to the removed terms below. Their text is TCW-74's.
- **Removed:**
  - `work-item/definition-of-done`;
  - `work-item/intake`;
  - `work-item/body-surface` (the body is the request document; there is no
    intake to fall back to);
  - the features `published-store-writes` and `external-work-tracker`.

`node` is left for TCW-73's rename sweep.

## Problem

After TCW-69, the repository holds two work models. Only the old one is
reachable.

1. **Every `tcw work` command goes through the 2.x store.**
   - `_store()` opens `FsWorkStore` (`tcw/work/cli.py:128-133`), a class of about
     4,500 lines (`tcw/store/fs.py:4306` to the end of the file).
   - That class implements `WorkStore`, the 35-method interface TCW-69's
     Problem 5 describes (`tcw/store/base.py:3386`).
   - TCW-69's model, backend protocol and `advance` are tested against an
     in-memory backend and used by nothing.
2. **The 2.x store keeps state in places 3.0 does not have.**
   - Status is a folder (`STORE_LAYOUT`, `fs.py:3782`; `WORK_STATUSES`,
     `base.py:989`), and a move is a `git mv` and a commit (`fs.py:849`,
     `fs.py:8219`, `fs.py:8249-8251`).
   - The store root carries:
     - `graveyard.yaml` (`fs.py:4323`);
     - `renames.yaml` (`fs.py:6416`);
     - `dod.yaml` (`fs.py:6977-6978`).
   - Writes are serialized by a lock kept in the git folder
     (`fs.py:5459`).
   - A new item's name gets a uniqueness suffix (`_unique_slug`,
     `fs.py:8442`) where 3.0 refuses.
3. **The 2.x tracker integration is woven through the commands.**
   - `tcw/tracker/` holds about 3,300 lines.
   - `tcw/work/cli.py` imports from it in 55 places (claims, sync, intake,
     ownership, progress).
   - Its configuration is parsed by `parse_tracker_config` (`base.py:1499`).

   TCW-71 replaces it with a Jira backend built on TCW-69's interface.
4. **Other surfaces read the 2.x store directly**, so removing the store breaks
   them unless they are rewired:
   - `tcw validate` opens `FsWorkStore` in five places
     (`tcw/validate.py:32`, `:125`, `:162`, `:185`, `:253`), checks retention
     and tracker settings (`validate.py:366-384`), and runs the 2.x capability
     gate over open items (`validate.py:268-295`);
   - `tcw capabilities drift` follows `Planning doc` fields into the work store
     and its graveyard (`tcw/capabilities/cli.py:200-254`);
   - `tcw://` work references resolve through `resolve_qualified_work_ref`
     (`tcw/refs.py:29-33`, `:132-169`; `fs.py:594`);
   - `tcw serve` serves the board through `FsWorkStore` and the tracker module
     (`tcw/serve/__init__.py:20-30`, `:492-509`);
   - `tcw init` scaffolds status folders and ignore rules (`fs.py:1215`), and
     `tcw provision` accepts a work store only when all six status folders exist
     (`_is_store_layout`, `fs.py:3832-3866`);
   - "is there a work store here" is answered by opening `FsWorkStore`
     (`_has_work_store`, `fs.py:545-561`).
5. **The prompt and lifecycle commands read 2.x configuration.**
   - `stage prompt`, `lifecycle` and `procedure prompt` resolve through
     `LifecyclePolicy`, parsed from `work.lifecycle` (`parse_lifecycle_policy`,
     `base.py:2966`).
   - TCW-69's configuration parser refuses `work.lifecycle` as a removed key.
6. **This repository cannot be read by 3.0 yet.**
   - Its `tcw-config.yaml` sets `work.tracker` (line 3), `work.retain`
     (line 77) and `work.lifecycle` (line 83).
   - Its board uses status folders.
   - TCW-76 migrates both, last.

   Until then, nothing in this slice can be tried against the repository's own
   board.

## Goals

1. **A filesystem backend** that implements TCW-69's eleven operations (the
   eight it started with, plus `read_request`, `read_comments` and
   `current_user`, the epic's decision 1) with the storage decisions in the
   ticket: `item.yaml`, date-prefixed folders, `request/request.md`,
   `comments/<UTC timestamp>.md`, inbox-stage items, rename with reference
   rewriting, delegation into filesystem-mode projects, and `lookup` returning
   `None`.
2. **One way to open a backend.** A single function opens the backend a project
   is configured for; the CLI, `validate`, `tcw://` references, `drift` and (in
   TCW-77) the viewer all go through it.
3. **`tcw work` runs on the 3.0 model.** Every command that reads or writes an
   item uses the backend, TCW-69's `advance` and its layout, with the flags and
   the stdout/exit behavior TCW-73's ticket already fixes for that command.
4. **The 2.x work store is gone.** Its code, its store-root files, its commands,
   the tracker integration, and their tests are deleted. Nothing left in `tcw/`
   reads or writes status folders, `graveyard.yaml`, `dod.yaml`, `renames.yaml`,
   `state.yaml` or `tracker.yaml`.
5. **Every surface that read the 2.x store reads the backend**, or is removed
   with a named owner who rebuilds it: `validate`, `drift`, `tcw://` references,
   `init`, `provision`, and `serve`.
6. **No git state changes** from any command this slice touches.
7. **A test suite that never needs this repository's board**, green on the epic
   branch while the repository's own config and board are still 2.x.

## Non-goals

- **The Jira backend** (TCW-71). This slice leaves two branches for it:
  - opening a project whose `work.backend` is `jira`;
  - delegating into one.

  Until TCW-71 lands, both fail with exit 1 and a message saying the Jira
  backend is not part of this build. `lookup` and the `tickets` commands are
  TCW-71's.
- **Personal configuration and identity** (TCW-72): `list --mine`,
  `--assign-me`, `user.name`, `inherit`, `config show`, and recording a comment's
  author. This slice implements the filesystem backend's `current_user`
  operation (Design 3.3), but nothing in this slice calls it, and the value it
  answers with comes from TCW-72's personal configuration.
- **The rest of the command surface** (TCW-73). This includes:
  - `--help` text;
  - the `tcw noun verb` naming pass;
  - `tcw init <axis>` replacing the per-axis `init` commands;
  - `tcw projects list` replacing `tcw work nodes`;
  - the taxonomy and capabilities commands;
  - the "node" to "project" rename;
  - removing git wording from messages;
  - the output format rules (the epic's decision 10: one identifier per stdout
    line, details through `--json`, the `--json` envelope, and which stream a
    `validate` finding goes to) and the user-facing description of them.

  Design 1 draws the line. The epic's decision 2 accepted it, and TCW-73 is
  implemented after this slice and TCW-71.
- **Prompt, procedure and skill text** (TCW-74, except `skills/configure/`,
  which the epic's decision 3 gives to TCW-75). This slice does not write
  `review.md` or `qa.md` prompts, rewrite `verify.md`, or change any skill.
- **Documentation** (TCW-75). This slice writes its changelog and release-notes
  entries and its capability and taxonomy records, and nothing else (Design 14).
- **The `Planning doc` and `Tracker` capability fields.** The epic's decision 9
  gives their removal from `CAP_FIELDS` and the capabilities commands to TCW-73,
  and their removal from records to TCW-76. This slice only stops `drift` from
  following them (Design 10.3).
- **Migrating this repository** (TCW-76): its `tcw-config.yaml`, its board, its
  `dod.yaml` and `graveyard.yaml`, and `scripts/require_artifact.py`.
- **The web viewer** (TCW-77). This slice removes the 2.x work routes and does
  not build new ones.
- **The `evals/` harness**, which seeds and grades fixtures with 2.x commands.
  The epic's decision 14 gives it to TCW-74. This slice only keeps its tests
  from failing in the meantime (Design 9).
- **`tests/cli/scenarios/`**, which the epic's decision 14 gives to TCW-73.

## Design

### 1. The boundary with TCW-73

**[Decision]** TCW-73's ticket fixes, for each `tcw work` command, what stdout
carries and which exit codes mean what. Writing the new commands to that contract
once costs nothing; writing them to a different one and changing them in TCW-73
would be wasted work. So the line is drawn by **what the 2.x store made
necessary**, not by command:

**TCW-70 does:**

- **Wire, with their final flags and TCW-73's stdout and exit codes**, every
  `tcw work` command that reads or writes an item:
  - `new`, `list`, `show`, `path`, `edit`, `advance`, `discard`, `comment`,
    `rename`;
  - `path --handoff`, which exposes TCW-69's handoff path (the epic's
    decision 18; TCW-73's surface table lists it under this slice);
  - one function that turns an item argument into a slug and a backend, used
    by every command above. TCW-73's spec names it `resolve_item` and fixes its
    rules (exact match, full slug or bare folder name); TCW-71 adds its Jira-key
    branch;
  - `--mine` and `--assign-me` are TCW-72's, because they need an identity.
- **Remove** every command whose implementation is the 2.x store or the tracker:
  - `start`, `submit`, `rework`, `complete`, `drop`, `delete`;
  - `inbox` (all subcommands), `tracker` (all subcommands), `tombstone`;
  - `reconcile`, `delegate`, `escalate`, `scaffold`;
  - `stage gate` (its replacement is `advance --dry-run`) and `stage validate`.
- **Rewire onto TCW-69's configuration**, keeping their current flags where the
  flag still means something:
  - `stage prompt`, `procedure prompt`, `lifecycle`, `docs`, `tags`;
  - `work init` and `tcw init`'s work component (Design 11).
- **Rewire** the surfaces in Problem 4 (Designs 10–12).

**TCW-73 does:** the naming pass, `--help` text, `tcw init <axis>`,
`tcw projects list`, the taxonomy and capabilities commands, the node-to-project
sweep, git wording in messages, the output format rules and the written
contract (the epic's decision 10). It may change how `show`, `lifecycle` and
`validate` present their text, and it adds the `--json` envelope. It does not
need to remove any `tcw work` command, because none of the ones on its
"removed" list survive this slice. It is implemented after this slice and
TCW-71 (decision 2).

**[Decision] What this slice's tests pin down, given that the format is
TCW-73's.** Where TCW-73's ticket already fixes a command's stdout (the slug, the
stage, one slug per line, nothing), this slice writes it and tests it exactly.
Where the format is still TCW-73's to fix (plain `show`, `lifecycle`, the
`--json` envelope, `validate`'s finding lines), this slice's tests assert the
content (which fields, which files and keys are named, the exit code), not the
layout, so TCW-73 can change the layout without rewriting them.

`tcw work nodes` keeps working unchanged until TCW-73 renames it; only its
"does this project have a work store" test changes (Design 3.5).

### 2. Opening a backend (`tcw/work/open.py`)

Every error named in this spec (`BackendError`, `UsageError`, `Refused`,
`NotFound`, `Unreachable`, `MovedWithoutNote`) is one of the exception classes
in `tcw/errors.py`, each carrying its exit code, as TCW-69 defines them (the
epic's decision 8). This slice adds no exception class of its own.

1. `open_backend(project_root) -> WorkBackend`.
   - It reads the project's tracked `tcw-config.yaml` through TCW-69's
     `parse_work_config`. Any problem is raised as `BackendError` (exit 1),
     naming every bad key. A removed 2.x key names the migration guide, as
     TCW-69's parser already does.
   - It resolves the work path (Design 3.4) and returns the backend for
     `work.backend`.
   - `filesystem` gives `FsWorkBackend`. `jira` raises `BackendError` until
     TCW-71 (Non-goals).
2. `open_project(project_id, here) -> WorkBackend` opens another project's
   backend for reading.
   - The project is resolved through the existing registry
     (`tcw/store/project.py`), which already covers `connected-projects` and
     `TCW_PROJECT_<ID>`. Only that project's tracked config is read.
   - A project that is declared but not present on this machine raises
     `Unreachable` (exit 5). This is the epic's decision 4, which settles the
     disagreement with TCW-73's draft (which proposed exit 4). TCW-69's
     reference check reports that case as "unresolved".
   - **[Decision]** An ID that no declaration names at all raises `NotFound`
     (exit 4), as TCW-73's spec has it (its Design 3.4): there is nothing to
     reach, so "try again later" would mislead.
3. `open_delegation_target(project_id, here) -> WorkBackend` opens another
   project for writing.
   - The project is resolved as above, except that an unknown ID is the
     first delegation condition failing: `Refused` (exit 3), as the ticket and
     the epic's decision 4 require, not exit 4.
   - A declared project not present on this machine is also `Refused`
     (exit 3), **unless** its connected-project entry carries a `jira` block.
     **[Decision, owner 2026-10-01]** In that case the function hands the
     entry to TCW-71's Jira adapter, which opens the target's Jira project
     from the block alone and creates the ticket in its inbox (TCW-71). This
     check comes first, before any filesystem condition, because none of
     them can be checked without the checkout. TCW-70 ships only the branch
     point: until TCW-71 lands, an entry with a `jira` block is refused with
     a message saying Jira delegation arrives with the Jira backend.
   - In filesystem mode it then checks the other two delegation conditions
     (Design 6). A failed condition raises `Refused` (exit 3) naming it.
   - Every rule specific to the filesystem lives in the filesystem adapter;
     the caller sees only "here is a backend" or "refused, because …".

### 3. The filesystem backend (`tcw/work/fs_backend.py`)

`FsWorkBackend(project, work_path, config, user_name=None)` implements TCW-69's
`WorkBackend`, all eleven operations, with `external_stages = frozenset()` and
`inbox_items = True`.

Three parts of TCW-69's model that the epic's decisions 1 and 16 added exist for
Jira and are inert here:

- `Item.untracked` (keys of linked tickets that have no item) is always the
  empty tuple. A filesystem reference is always a slug.
- `Item.priority` is never `None`. `None` means a Jira project without the
  priority field; here an absent `priority` reads as `medium` (3.2).
- `Refused` never carries a ticket key.

#### 3.1 Item folders

1. **An item folder** is a directory directly inside the work path whose name
   matches `^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*$`, is at most 128
   characters, starts with a real calendar date, and holds an `item.yaml`.
   - Nothing is searched for at any depth below the work path. Nesting gives
     no meaning: a parent is the `parent` property.
2. **The name** is `<date>-<title words>`:
   - `<title words>` is TCW-69's `title_words(title)`;
   - `<date>` is the creation date. **[Decision]** It is the local calendar
     date, as 2.x uses (`fs.py:8440-8442`), because a person reads it as "the
     day I made this". Comment and handoff timestamps stay in UTC, as the
     ticket and TCW-69 say.
3. **`Item.created`** is the date parsed from the name. There is no `created`
   key in the file.
4. **A name that already exists is refused** (`Refused`, exit 3), naming the
   existing folder. There is no `-2` suffix.

#### 3.2 `item.yaml`

1. **Keys.** A mapping with exactly these keys, written in this order, with an
   absent property left out:
   - `title`: a non-empty string. Required.
   - `stage`: a string. Required.
   - `priority`: one of TCW-69's `PRIORITIES`.
   - `effort` and `complexity`: each one of TCW-69's `SIZES`.
   - `tags`: a list of tags.
   - `assignee`: a string.
   - `parent`: a slug.
   - `blocked-by`: a list of slugs.

   Empty lists are left out.
2. **Writing.**
   - Slugs are always written in full (`project/folder`).
   - The file is rewritten whole on every change.
   - **[Decision]** A comment a person adds to `item.yaml` by hand is not kept.
     The file belongs to TCW, as `state.yaml` did.
   - Writes go to a temporary file in the same folder, which then replaces
     `item.yaml` in one step. A reader therefore never sees a half-written
     file.
3. **Reading.** **[Decision]** Strict, with one exception.
   - An `item.yaml` that is unreadable, not a mapping, has an unknown key, lacks
     `title` or `stage`, or holds a value outside its scale or type, makes the
     item **unreadable**: `read` raises `BackendError` (exit 1) naming the file
     and the key.
   - **The exception is the stage value.** A `stage` that is not an enabled flow
     or terminal stage in TCW-69's table reads as **no stage**
     (`Item.stage = None`). That covers a misspelling, a stage the project has
     since disabled, a side stage, and `verify` left over from 2.x.

     This reuses TCW-69's rule for a Jira ticket in an unmapped status, so
     nothing new is needed:
     - `list` shows such an item by default;
     - a bare `advance` refuses it;
     - `advance --to <stage> --force --reason …` gives it a stage again.
   - An absent `priority` reads as `medium`, the value `new` writes.
   - A tag missing from the registry is kept on read; `validate` warns about it
     (Design 10). This lets a project remove a tag from its registry without
     making items unreadable.
   - A `parent` or `blocked-by` entry written as a bare folder reads as this
     project's, through TCW-69's `Slug.parse`.

#### 3.3 The operations

1. **`create(title, props, *, stage, request)`**
   - It validates `props` through TCW-69's shared checks.
   - It makes the folder. A failure after that point removes the folder it
     just made, so a failed `create` leaves nothing behind. This is the only
     place TCW removes a folder, and only one it created in the same call.
   - It writes `item.yaml` with `title`, `stage`, `priority` (default `medium`)
     and the given properties.
   - When `request` is given, it writes the text **verbatim** to the request
     document, whatever the starting stage. **[Decision]** That includes an
     inbox item: piped text is the request's first draft, and the request
     stage revises it in place. There is no `intake.md`. The path comes from
     TCW-69's `layout.path` for the first flow stage whose artifact is a
     document. This module contains no stage name (Design 13).
2. **`read(folder)`.** Returns the `Item`. A missing folder raises `NotFound`
   (exit 4).
3. **`list(query)`.**
   - It reads every item folder in the work path, applies TCW-69's `Query`
     rules, and returns the items in folder-name order, which is creation date
     and then name.
   - Directories that are not item folders and plain files are not items, and
     are skipped.
   - **[Decision, owner 2026-10-01]** `Query.tags` (TCW-69's Query, item 1) is
     matched against the `tags` list of each `item.yaml`: when it is not
     `None`, an item is returned only if it carries at least one of the given
     tags. The given tags are compared with the item's tags as read (3.2),
     both in the canonical form `normalize_tag` gives, as 2.8 does. There is
     no lookup in the tag registry, because an item may carry a tag the registry no
     longer has (3.2). An item with no `tags` key matches no tag filter. The
     tag filter combines with the stage, parent and assignee filters (an item
     must pass all of them).
   - **[Decision, owner 2026-10-01]** If any item folder is unreadable, `list` raises
     `BackendError` naming every unreadable `item.yaml`. It does not hide part
     of the board. `tcw validate` reports the same files with the key at fault
     (Design 10).
4. **`update(folder, changes)`.** Reads, applies TCW-69's `Changes` and checks,
   and writes. Stage is not part of `Changes`.
5. **`set_stage(folder, stage, note)`**
   - It writes the new `stage` to `item.yaml` and then, when `note` is given,
     writes the note as a comment (3.3.6).
   - If the comment cannot be written, it raises `MovedWithoutNote`, and the
     move stands.
   - It returns the stage it reads back from the file.
   - It never raises `Refused`, because the filesystem has no workflow that can
     refuse a move. TCW-69's `advance` has already checked the move.
6. **`comment(folder, text)`**
   - It writes `text` verbatim to `comments/<YYYYMMDDTHHMMSSZ>.md`, using the
     current UTC second. Empty or whitespace-only text is a `UsageError`.
   - The file is created only if no file with that name exists. **[Decision]**
     If that name is taken (two comments in one second), the next free second
     is used, so no comment ever overwrites another and the order by name stays
     the order of writing. This is a small departure from the handoff rule in
     TCW-69 (which refuses), because a trace comment is written by TCW during a
     move and refusing it would turn every quick second comment into exit 6.
   - The file holds only the text. Who wrote it is TCW-72's question (Notes).
7. **`rename(folder, title_words)`**: Design 5.
8. **`lookup(name)`.** Always `None`.
9. **`read_request(folder)`.** Returns the text of the request document,
   verbatim, or `None` when the file does not exist. The path is the one
   `create` writes (3.3.1), from TCW-69's layout. **[Decision]** The
   filesystem backend answers from the file rather than always returning
   `None`, so a caller (TCW-73's `show`, TCW-74's prompts, TCW-77's viewer)
   reads the request one way in both modes and never branches on the backend.
   A missing folder raises `NotFound` (exit 4).
10. **`read_comments(folder, limit)`.** Reads `comments/*.md` whose names match
    the timestamp pattern of 3.3.6, and returns at most `limit` of the newest,
    as TCW-69's `Comment` values, in the order TCW-69 defines for the
    operation.
    - `at` is parsed from the file name, in UTC; `text` is the file's
      content, verbatim; `author` is `None` (TCW-72 may add one, Notes).
    - **[Decision]** Other files in `comments/` are ignored, as `list` ignores
      folders that are not items. A file whose name matches but cannot be read
      as UTF-8 raises `BackendError` naming it, matching the strict reading
      of 3.2.
    - No `comments/` folder means no comments, not an error.
11. **`current_user()`.** Returns `user_name` when the backend was built with
    one. Otherwise it raises `BackendError` (exit 1) saying no identity is
    configured. **[Decision]** This slice always builds the backend with no
    `user_name`, because the only source TCW-72 allows is `user.name` in
    personal configuration, which TCW-72 adds; TCW-72 passes the value in
    `open_backend` and writes the final message text (its Design 9). No
    command in this slice calls `current_user`; the contract tests cover both
    answers.

#### 3.4 Where the work path is

The work path is resolved exactly as today, by `resolve_store`
(`fs.py:3894`). The order is:

- `work.path`;
- else `docs/work`;
- a relative path re-anchored inside a linked worktree;
- a declared `work.repository`, and its provisioned checkout.

Only what "usable" means changes (3.5). The capabilities
`configure-the-work-store-location` and `declare-the-work-stores-home-repository`
keep working, minus their mentions of commits and publishing.

#### 3.5 "Has a work store"

**[Decision]** A work store is present when the resolved work path is a
directory. Nothing inside it is required: an empty store is a real state, and 3.0
has no status folders to look for. The same test serves:

- `_is_store_layout` for `tcw provision` (`fs.py:3832-3866`), which becomes the
  same "the directory is there" answer the tree stores already get;
- `_has_work_store` (`fs.py:545-561`), used by `tcw work nodes`;
- the delegation condition "its work store is present".

### 4. Branches, concurrency and git

1. **Each branch carries its own `stage`**, as the ticket says. There is no
   history list, so two branches conflict only when both changed the same
   `item.yaml`.
2. **TCW never changes git state.**
   - No module this slice adds or keeps runs `git add`, `commit`, `mv`, `rm`,
     `reset`, `checkout`, `merge`, `worktree`, `push`, `pull` or `fetch`. One
     exception is not a write: `tcw provision` clones a declared store. Its
     `--refresh` fetch and checkout stay as they are, because they act on the
     clone TCW made, never on the project's own repository; TCW-73 reviews them
     with the rest of the git wording.
   - Git is otherwise only read: to find a repository root and re-anchor
     paths inside a worktree (as today), and to run `git status --porcelain`
     for the delegation check.
3. **The 2.x machinery that existed only to commit goes.** That is:
   - the auto-commit of transitions;
   - publishing to a remote;
   - the store lock (`fs.py:5459`);
   - claim staging (`.claiming/`);
   - the worktree commands.
4. **stderr names every file written, moved or removed.**
5. **The order of a write.** Each operation writes whole files, each replaced
   in one step, in a fixed order:
   - `create`: folder, then `item.yaml`, then the request;
   - `set_stage`: `item.yaml`, then the comment.
6. **[Decision] No lock.** Two commands changing the same item at the same
   moment on one machine can lose one change: the last write wins. This is
   accepted for simplicity. The case that matters in practice is two branches,
   and git reports that as a conflict. The 2.x lock lived in the git folder,
   which a non-git store does not have.

### 5. Rename

`tcw work rename <slug> <new name>`, printing the new slug on stdout.

1. **The new name.**
   - It is either the part after the date, or a full folder name with the
     **same** date. A different date is a `UsageError`.
   - **[Decision]** The words must already match the folder-name pattern.
     Otherwise it is a `UsageError` whose message shows `title_words` of the
     argument as a suggestion. Nothing is reshaped silently.
   - The title does not change; `edit --title` does that.
2. **Allowed at any stage.** **[Decision]** Finished items too. TCW-69 says
   folders never move "by TCW" as a stage change; a rename is an explicit
   request.
3. **Steps, in order:**
   1. Refuse (`Refused`, exit 3) if the new folder exists.
   2. Read every item in this project. Find those whose `parent` or `blocked-by`
      names the old slug, in either written form.
      - If any item is unreadable, refuse before moving anything (`BackendError`,
        exit 1), naming it. An item that cannot be read might hold a reference
        that would then be missed.
   3. Move the folder with one filesystem rename (never `git mv`).
   4. Rewrite each referencing `item.yaml`, writing the new slug in full.
   5. Search the text files inside this project's work path for the old folder
      name, and print each match as `path:line` on stderr, as "not rewritten".
      **[Decision]** The search covers only the work path. Changelogs, code and
      other repositories are not searched. Items in other projects are never
      rewritten; stderr says so, and `tcw validate` in those projects reports
      the stale reference (TCW-69 Design 9).
4. **A failure after step 3** stops, keeps what was done, and lists the items
   not rewritten (exit 1). **[Decision]** There is no rollback. Every remaining
   stale reference is then a `validate` warning that names it.
5. There is no `renames.yaml`, no alias for the old name, and no lock.

### 6. Delegation into another filesystem-mode project

1. **Entry points.**
   - `tcw work new "<title>" --project <id>` creates the item in project `<id>`.
   - `edit <slug> --blocks <other-project>/<folder>` updates the other
     project's item's `blocked-by`.
   - Both open the target with `open_delegation_target` (Design 2.3).
   - Any other write to another project's item is refused (exit 3), with a
     message saying to run the command in that project, as TCW-73's
     Design 3.4 states.
2. **Which projects.** **[Decision]** Any project the registry can locate from
   here by ID. That is the same set a cross-project reference resolves against.
   There is no longer a "child" verb and a "parent" verb. This includes an
   upstream project (one that does not name this project): the three
   conditions already make sure the target exists, has a store, and has
   nothing uncommitted, and the files are left uncommitted for a person in
   that repository to review. One rule ("any project you can reach") is simpler
   than a rule that depends on the direction of the declaration.
   **[Decision, owner 2026-10-01]** The owner confirmed that delegation may
   write into the target's checkout once the three conditions below pass.
3. **The three conditions**, checked in this order. The first failure refuses
   (exit 3) with a message naming it, and nothing is written:
   1. **The project's path resolves.** An undeclared ID and a project declared
      but not present on this machine both fail here (the epic's decision 4).
   2. **Its work store is present** (Design 3.5).
   3. **The store has no uncommitted changes.**
      - `git status --porcelain --untracked-files=all -- <work path>`, run in
        the repository that holds the store, prints nothing. Ignored files do
        not count.
      - **[Decision]** A store that is not inside a git repository fails this
        condition, because it cannot be checked.
      - **[Decision]** This check is a plain function in `tcw/work/open.py`,
        `uncommitted_changes(path) -> list[str]`, not part of the filesystem
        adapter, because TCW-71's delegation into a Jira-mode project checks
        the same thing for the item folders it keeps in git (TCW-71 asked for
        it to be callable). It only reads git.
4. **The created item.**
   - It lands at the target's first flow stage (inbox).
   - It is validated against the **target's** tag registry and properties.
   - `parent` and `blocked-by` may name items in any project.
   - stdout prints the target slug (`<id>/<folder>`). stderr names each file
     written and says it is uncommitted in the target's repository. The exit
     code is 0 (TCW-73's exit table lists "delegation that stopped at the
     target's inbox" under 0).
5. **A Jira-mode target** refuses with exit 1 until TCW-71 (Non-goals).

### 7. The `tcw work` commands

The table lists every `tcw work` command after this slice. The slug argument
is resolved by the one function of Design 1 (TCW-73's `resolve_item`): the full
slug or a bare folder name (TCW-69's `Slug.parse`), exact match only, with no
prefix matching. In the stdout column, "slug" always means the full slug.

| Command | stdout | Notes |
| --- | --- | --- |
| `new "<title>" [props] [--stage inbox] [--project <id>]` | the slug | Reads request text from stdin when stdin is not a terminal. `--stage` accepts only the first flow stage. |
| `list [--stage <s>]… [--tag <t>]… [--parent <slug>] [--assignee <a>] [--all] [--json]` | one slug per line, or the records of 7.1 with `--json` | `--stage` and `--all` together are a usage error (TCW-69). `--stage` repeats. **[Decision, owner 2026-10-01]** `--tag` stays and fills `Query.tags`: it repeats, and an item carrying any of the given tags matches. Its value is parsed as 2.8 parses it today (`tcw/work/cli.py:4968-4969`: the `--tags` alias and a comma-separated value), so nothing about the flag changes in this slice; TCW-73 owns its final spelling. `--tag` combines with `--stage` and with `--all`. |
| `show <slug> [--json]` | the record | See 7.1. |
| `path [<slug> [<stage> [--next \| --handoff]]]` | one absolute path | TCW-69's `path`, including its handoff form behind `--handoff` (the epic's decision 18). `--next` and `--handoff` together are a usage error (exit 2). **[Decision]** With no slug it prints the work store folder, as today, so a script can still find the store. |
| `edit <slug> [props] [--blocks <slug>]…` | nothing | Property flags as TCW-73 lists, minus `--assign-me`. An empty value clears an optional property (`--assignee ""`). |
| `advance <slug> [--to <s>] [--force --reason <r>] [--dry-run]` | the stage | Calls TCW-69's `advance`. Exit code is the outcome's. |
| `discard <slug> --reason <r>` | the stage | TCW-69's `discard`. |
| `comment <slug>` | nothing | Text from stdin. |
| `rename <slug> <new name>` | the new slug | Design 5. |
| `stage prompt <stage> [<slug>]` | the text | See 7.2. |
| `procedure prompt <id> [<slug>]`, `docs`, `lifecycle` | the text | Rewired onto TCW-69's config. `lifecycle` prints the enabled stage table with each stage's `prompt`, `pre` and `post` bindings. Its options that name transitions go; the plan lists which. |
| `tags list \| add \| rm` | as today | The tag registry is edited in `tcw-config.yaml` without the store. |
| `nodes` | as today | TCW-73 renames it. |
| `init` | as today | Scaffolds the 3.0 work folder (Design 11). TCW-73 merges it into `tcw init <axis>`. |

Every property flag is checked through TCW-69's shared validation. The errors
are its usage errors (exit 2). A config error is exit 1, from every command
that loads config.

#### 7.1 The item record

**[Decision]** One record, used by `show --json`, each entry of `list --json`,
and the JSON a `generate:` prompt binding receives in place of 2.x's
`work_item_json` (`tcw/work/projection.py`). It has these keys:

- `slug`, `title`, `stage` (`null` when there is none), `created`
  (`YYYY-MM-DD`);
- `priority`, `effort`, `complexity`, `tags`, `assignee`, `parent`,
  `blocked-by`;
- `blocks`, derived by TCW-69's `blocks_of` within this project;
- `children`, the slugs whose `parent` is this item, within this project;
- `path`, the item folder.

- `untracked`, TCW-69's `Item.untracked` (the epic's decision 16). It is
  always `[]` in filesystem mode, and is in the record so that the record has
  the same keys in both modes.

Absent properties are `null` or `[]`. The record does not carry the request
text or the comments; a caller that wants them uses `read_request` and
`read_comments` (Design 3.3).

The epic's decision 10 makes the output format TCW-73's. So this slice fixes
the **field set** (TCW-73's spec agrees it is this slice's), and TCW-73 fixes
the envelope around it (its `"schema"` key and the named list key) and how
plain `show` lays the fields out. Until TCW-73 lands, `show --json` prints one
record, `list --json` prints a JSON array of records, and plain `show` prints
one `key: value` line per field.

A `generate:` binding's script runs with the project root as its working
directory and `TCW_SLUG` set to the full slug, as TCW-69's hooks do (the
epic's decision 11).

#### 7.2 `stage prompt` without a packaged prompt

`stage prompt` composes the stage's `work.stages.<stage>.prompt` bindings with
the packaged `tcw/work/prompts/<stage>.md`. TCW-74 writes `review.md` and
`qa.md`.

**[Decision]** Until then, a stage whose `prompt` column is yes and whose
packaged file is missing fails with exit 1, naming the missing file. A packaging
gap should be loud, not an empty prompt. The header that `stage prompt` adds
names `advance --dry-run` instead of `stage gate`.

### 8. Configuration

- Every command that reads config goes through `open_backend`, and therefore
  through TCW-69's `parse_work_config`.
- The 2.x parsers go: `parse_lifecycle_policy` (`base.py:2966`),
  `parse_tracker_config` and its helpers (`base.py:1255-2010`), and
  `parse_retention`.
- The pure helpers TCW-69's plan lists move out of `base.py` if it is cut down:
  `normalize_tag`, `parse_documentation_entries` and `PROCEDURE_IDS`.
- The hook runner `run_bindings` stays (TCW-69 plan, "What the new code imports
  from 2.x"). It already runs each binding with the project root as its
  working directory (`tcw/work/hooks.py:94`). The 2.x environment it builds
  (`TCW_STATUS`, `TCW_TRANSITION`, `TCW_NODE_ROOT`, a bare-folder `TCW_SLUG`;
  `hooks.py:61-69`) is replaced by the variables TCW-69's Design 6.5 lists,
  with `TCW_SLUG` the full slug (the epic's decision 11). How a 2.x hook's
  variables map to 3.0 is described by meaning in TCW-76's guide; this slice
  writes no compatibility names.

A project whose config still has 2.x keys gets exit 1 from every `tcw work`
command, naming each key and the migration guide. This repository is such a
project until TCW-76.

### 9. What is deleted

Code:

- `FsWorkStore` and the work half of `tcw/store/fs.py`, including:
  - graveyard, renames, retention, DoD, claims and sidecars;
  - inbox entries;
  - publication, worktree and merge helpers.

  The taxonomy and capabilities stores, the registry, provisioning and the
  location ladder stay.
- From `tcw/store/base.py`:
  - `WorkStore`, `WorkItem` and `Tombstone`;
  - the status and transition tables, `STAGE_IDS` and `LIFECYCLE_STEPS`;
  - `TrackerConfig` and the binding sidecar types;
  - `DEFAULT_DOD`, `WORK_ARTIFACTS` and `WORK_SIDECARS`.
- The whole `tcw/tracker/` package, except its HTTP client.
  **[Decision]** `tcw/tracker/jira.py` imports nothing from TCW
  (`tcw/tracker/jira.py:27-37`), so it is **moved** in this slice's change, not
  deleted, to `tcw/work/jira/client.py`, unchanged, as TCW-71's spec asks (its Design 14).
  Its fake, `tests/tracker_fake.py`, moves to `tests/work/jira/fake.py`, and
  the transport tests in `tests/test_tracker_client.py` move to
  `tests/work/jira/test_client.py`. Those tests build their configuration from
  `TrackerConfig` (`tests/test_tracker_client.py:26`, `:29-37`), which this slice
  deletes, so they get a small local stand-in with the same attribute names;
  the client reads its configuration only through attributes
  (`jira.py:115-124`). Moving costs this slice little and saves TCW-71
  restoring the files from history. The note in `tcw/tracker/__init__.py:9-11`
  that the client is the single home of Jira HTTP work moves with it.
- `tcw/work/recursion.py`, keeping only what TCW-69 moved into `gates.py`.
- `tcw/work/projection.py` and `tcw/work/templates.py`.
- The parts of `tcw/work/hooks.py` and `tcw/work/resolve.py` that take 2.x
  types.
- `tcw/work/cli.py`, replaced.

**Tests.** **[Decision]** A test file goes with the code it tests. A test of
behavior that survives is **ported**, not deleted. That covers:

- location resolution and worktree re-anchoring;
- provisioning and the project graph;
- `tcw://` resolution;
- `stage prompt` composition, hooks and timeouts;
- stdin handling and tag registry editing.

**[Decision] Tests whose subject another slice rewrites are skipped, not
deleted.** `tests/test_skill_flow.py`, `tests/test_prompt_fallback.py` and the
five `tests/test_eval_*.py` files drive the 2.x CLI to test skills, prompts and
the `evals/` harness, which TCW-74 rewrites (the epic's decision 14). Each gets a
module-level skip, placed before its imports, whose reason names TCW-74, as
TCW-74's spec asks. TCW-74 removes the skip when it rewrites the file. Any other
test of a later slice's subject is handled the same way, naming that slice.

`tests/test_repo_lifecycle.py` and the `self` case of
`tests/test_lifecycle_baseline.py` read this repository's 2.x `tcw-config.yaml`
and are deleted (Design 15.1). TCW-76 writes their 3.0 replacement when it
migrates the configuration, as its spec says.

The plan lists every file in `tests/` that imports a deleted name, with its fate
and the reason. About 119 of the 159 test files touch the work axis today.

### 10. `tcw validate` and `tcw capabilities drift`

1. **Work checks.** These replace `_open_sidecar_problems`, the retention and
   tracker checks, and `FsWorkStore.check()` (`validate.py:268-295`,
   `:366-384`). For a filesystem-mode project, `validate` reports:
   - an `item.yaml` that is unreadable, with the file and the key (error);
   - an item whose `stage` reads as no stage, with the value found (error);
   - a directory in the work path that is not an item folder (error);
   - a plain file in the work path other than hidden files (warning). This
     includes a leftover `dod.yaml`, `graveyard.yaml` or `renames.yaml`;
   - a tag not in the registry (warning);
   - TCW-69's `reference_problems` over `list(Query(all=True))` (warnings, and
     "unresolved" lines). Other projects are resolved with `open_project`;
   - TCW-69's `stage_problems` (warnings);
   - TCW-69's `records_problems(finished=False)` for every unfinished item
     (errors). The file it checks is `<item>/capabilities.yaml`, at the item
     root (the epic's decision 19).

   The first five checks, which read only the files in the work path, are
   **[Decision]** one plain function of `tcw/work/fs_backend.py`, not an
   operation of `WorkBackend`, because only `validate` calls them. TCW-73's
   spec asks for exactly this (its Design 6.1.5), and TCW-71 supplies the Jira
   equivalent.

   **[Decision] The two "not part of a work store" messages** (a directory that
   is not an item folder, and a plain file) always end with "see
   `docs/migration-guide-2.8-to-3.0.0.md` for the work store layout". The text
   is the same whatever the entry is called, so no code recognizes 2.x, as
   TCW-76's ticket requires; but a 2.x project whose config never set a
   removed key, and so never hits the parser's pointer to the guide, is still
   pointed at it, as TCW-76's spec suggests.

   The `resolve` callback `reference_problems` takes (TCW-69 Design 9) answers:
   - `found` when `read` returns the item;
   - `missing` when the project is reachable and `read` raises `NotFound`, and
     **[Decision]** also when no declaration names the project at all
     (`NotFound` from `open_project`, Design 2.2), because that reference can
     never resolve from anywhere and should be fixed;
   - `unresolved` when `open_project` raises `Unreachable`: the project is
     declared but not present on this machine (the epic's decision 4).

   This slice wires `records_problems`, `reference_problems` and
   `stage_problems`, which TCW-69 and TCW-73's ticket had given to TCW-73,
   because the check they replace is built on the deleted store. The epic's
   decision 2 confirmed the move.
2. **Warnings.** **[Decision]** Neither a warning nor an unresolved reference
   fails the command: exit 0 when there are only those, as TCW-73's exit table
   says. Errors keep exit 1. Until TCW-73 lands, warnings print as
   `warning: …` and unresolved references as `unresolved: …`, on today's
   stream. Which stream findings go to and their exact layout are TCW-73's
   (the epic's decision 10; TCW-73's spec moves them to stdout), so this
   slice's tests read both streams and assert only that each finding names its
   file and key, and the exit code.
   The YAML well-formedness scan keeps working, with `item.yaml` replacing
   `state.yaml`, `tracker.yaml`, `graveyard.yaml` and `renames.yaml` in
   `OWNED_YAML_NAMES` (`fs.py:1510-1512`).
3. **Drift.** **[Decision]** `tcw capabilities drift` stops following
   `Planning doc` fields into the work store (`capabilities/cli.py:200-254`).
   - It runs TCW-69's `drift_problems` over the items at the completion stage.
   - The other kind of drift it reports (inherited capabilities never reviewed
     locally) is unchanged.
   - This also moves from TCW-73, for the same reason as 10.1, and so does
     rewriting the `detect-capability-drift` record (the epic's decision 2).
   - The `Planning doc` and `Tracker` fields themselves are settled by the
     epic's decision 9: TCW-73 removes them from `CAP_FIELDS` and the
     capabilities commands, and TCW-76 removes them from records. This slice
     only stops reading them.

### 11. `tcw init` and `tcw provision`

- `init` for the work component makes the work path and a `.gitkeep`. It no
  longer makes status folders or writes ignore rules for resolved items.
- A store being relocated by `init --work-path` is refused when the old store
  holds any item folder, instead of today's status-folder check.
- `provision` clones a declared work repository as today. A store counts as
  present by Design 3.5.

### 12. `tcw://` references and `tcw serve`

1. **References.** A work reference `tcw://W/<folder>` or
   `tcw://<project>/W/<folder>` resolves by reading the item through
   `open_backend` or `open_project`. It is OK when the item exists, at any
   stage. There is no resolved-item record any more, because folders are never
   deleted by TCW. A project that is declared but not on this machine is
   reported as unresolved, and one no declaration names as missing, matching
   `validate` (Design 10.1).
2. **`tcw serve`.** **[Decision, owner 2026-10-01]** The 2.x work routes are removed from
   `tcw/serve/__init__.py`, with their tests and Playwright specs.
   - Requests to `/api/work…` answer 404.
   - The taxonomy and capabilities routes keep working.
   - TCW-77 rebuilds work on `open_backend` and the item record (7.1).

   Porting the 2.x routes onto the backend first would be thrown away by
   TCW-77's rewrite. Nothing on the epic branch ships before 3.0.0, so the gap
   is never released. The owner confirmed on 2026-10-01 that no work pages are
   served between this slice and TCW-77.

### 13. No stage names outside the table

TCW-69's criterion 5 forbids stage-name literals in its modules.

- **[Decision]** The rule extends to `tcw/work/fs_backend.py`,
  `tcw/work/open.py` and the new `tcw/work/cli.py`.
  - The request document comes from the layout and the stage table.
  - `--stage inbox` and the delegation landing stage are "the first flow
    stage".
  - The completion stage for `drift` is found by its column.
- Help text and docstrings are exempt, as in TCW-69.

### 14. Documentation in this slice

`CLAUDE.md` asks every change to run `documentation-sync`. Its entries map like
this:

- The changelog and release-notes entries are written, named by this item's
  folder name. The release-notes entry starts with its first `##` heading and
  has no text before it; only TCW-75's entry carries the 3.0.0 introduction
  (the epic's decision 15).
- The capability and taxonomy records above are written.
- **[Decision]** The rest is deferred to the slices that own it: README and
  guides to TCW-75, every skill and agent to TCW-74 except
  `skills/configure/`, which goes to TCW-75 (the epic's decision 3).

Deferring has one cost. `tests/test_documented_cli_surface.py` fails for every
removed command a document still names. The epic's decision 6 settles how this
is handled, and it replaces the "smallest edit" rule TCW-75's draft proposed
(deleting the line in each document that names a removed command):

- the test gets a **temporary allowance**, a module this slice creates with two
  named lists: the commands this slice removes, and the configuration keys
  TCW-69's parser now refuses that documents still name (`work.lifecycle`,
  `work.tracker`, `work.retain` and the others the plan lists);
- a guard test asserts every command in the list really is absent from the
  CLI, and every key really is refused by `parse_work_config`, so the list
  cannot hide a new mistake;
- `DOCUMENTED_VERBS` (`tests/test_documented_cli_surface.py:261-262`), the list
  of verbs that must be findable in the guides, loses the three this slice
  removes: `tcw work stage gate`, `tcw work scaffold` and `tcw work tracker`;
- TCW-71 and TCW-73 add their own removals to the allowance; TCW-74 and TCW-75
  shrink it as they rewrite text; TCW-76's "validate clean" step requires it
  to be empty before 3.0.0 is cut (decision 6).

### 15. Driving this repository's board, and testing

1. **Tests never use this repository's board or config.**
   - Every new test builds its project in a temporary git repository, with
     `tcw init` run from the branch's code, as TCW-69's plan sets up (a virtual
     environment for the branch's checkout).
   - The 2.x tests that read the repository's own config
     (`tests/test_repo_lifecycle.py`, the `self` case of
     `tests/test_lifecycle_baseline.py`) are deleted with the parser they guard.
2. **The backend contract is tested once, against both backends.** TCW-69's
   memory-backend tests become a contract module, parametrized over
   `MemoryBackend` and `FsWorkBackend`. TCW-71 adds a third parameter for a
   stubbed Jira backend.
3. **The board is driven by editing files** for the whole epic branch, as
   `CLAUDE.md`'s exception requires and the epic's decision 7 confirms. That
   means the 2.x files: `state.yaml`, status folders and artifacts.
   - Each slice's Jira ticket is moved by hand when its item moves (In
     Progress, In Review, Done), because the tracker sync is one of the
     things this slice deletes (decision 7).
   - The branch's own `tcw` refuses this repository's config with exit 1
     (Design 8). That is the safe failure: it cannot misread the 2.x board.
   - A read-only view may come from a released 2.8 `tcw` installed outside the
     checkout (for example with `pipx`), run against the branch's board. The
     branch's code never reads it.
   - TCW-76 converts the board and config in the same change that switches
     the repository to 3.0, as its ticket says.
4. **CI runs bare `pytest`** (the repository's memory notes it). The suite must
   be green that way on the epic branch, with `tcw-config.yaml` still 2.x.

## Abstraction litmus test

| Operation or rule | Verdict |
| --- | --- |
| The eleven operations | **Backend interface**, implemented by this adapter. Jira implements each one (TCW-69, TCW-71). `read_request` and `read_comments` read files here and the ticket in Jira; `current_user` answers from `user.name` here and from the credentials' account in Jira. |
| `Item.untracked`, `priority: None`, a ticket key on `Refused` | **Model fields** a Jira store needs; this adapter leaves them empty, never `None`, and absent. |
| `item.yaml`, the folder name and date prefix, comment files | **Adapter details.** The model sees `Item`, `Item.created` and `comment(text)`. |
| Listing direct children that hold `item.yaml` | **Adapter detail**, and bounded: named entries, never a recursive search. |
| Rename as a folder move plus rewriting references | The **`rename` operation**. Jira renames only the part after the key. The stderr search for other mentions is an adapter-local text search, advisory only, and not an interface operation. |
| The delegation conditions | **Adapter-private**, behind `open_delegation_target`. Jira's conditions differ (TCW-71). The caller sees a backend or a refusal. |
| `open_backend`, `open_project` | **Model-level dispatch** on `work.backend`. Locating a project stays in the registry. |
| `tcw://` work references, `validate` references, `drift` | Built on `read` and `list`, not on paths. |
| `validate`'s item-folder checks | **Adapter-specific checks**, a function of the adapter module and not an interface operation; the filesystem's equivalent of TCW-71's offline key check. |
| `uncommitted_changes(path)` | **A git read shared by both delegation paths**, outside the interface; a store that is not in git fails the condition rather than skipping it. |

## Harness compatibility

Everything this slice guarantees lives in the `tcw` CLI, so Claude and Codex get
the same behavior. It adds no hook, skill or injected context. The board-driving
rule in Design 15 is plain instructions in `CLAUDE.md` and `AGENTS.md`, which
both harnesses read.

## Acceptance criteria

All criteria are checked by pytest unless they say otherwise. Fixtures are
temporary git repositories built with the branch's `tcw init`. "Through the CLI"
means calling `tcw.cli.main` with captured streams. The criteria marked
**(installed)** run the console script in a subprocess, because they are about
streams and exit codes as a shell sees them.

1. **Contract.** The contract module passes for both `MemoryBackend` and
   `FsWorkBackend`. It runs every case of TCW-69's memory-backend tests that is
   not specific to the memory backend, covering all eleven operations. For
   `FsWorkBackend` it also checks:
   - every `Item` read has `untracked == ()` and a `priority` that is not
     `None`;
   - `current_user()` returns the `user_name` it was built with, and with none
     raises `BackendError` (exit 1).
2. **Create.**
   - `tcw work new "Add a widget"` prints exactly `<id>/<today>-add-a-widget`
     followed by a newline on stdout **(installed)**, where `<today>` is the local
     date.
   - The folder's `item.yaml` is exactly `title: Add a widget`,
     `stage: request`, `priority: medium`, in that order and with no other key.
   - There is no `created`, `slug` or `history` key, and no `request/` folder.
   - Running the same command again the same day exits 3 and names the
     existing folder. No `-2` folder appears.
   - `new "!!!"` creates `<today>-untitled`.
3. **Request text.**
   - `printf 'line one\n' | tcw work new "X"` writes `request/request.md`
     with exactly `line one\n`.
   - `--stage inbox` with piped text writes `stage: inbox` and the same
     request file.
   - `read_request` returns `line one\n` for that item, and `None` for an item
     created with no piped text.
   - No command writes `intake.md`.
4. **Reading.** Each of these makes `show` exit 1 with a message naming
   `item.yaml` and the key:
   - an `item.yaml` with an unknown key `created`;
   - one missing `title`;
   - one with `priority: 3`;
   - one that is not valid YAML.

   An `item.yaml` with `stage: verify` reads with no stage. So does one with
   `stage: plan` when plan is disabled:
   - `show --json` gives `"stage": null`;
   - a bare `advance` exits 3;
   - `advance --to spec --force --reason r` moves it.
5. **Listing.**
   - A default `list` shows inbox-stage and no-stage items and hides
     completed and discarded ones.
   - `list --stage inbox` shows only inbox items. `list --all` shows all.
   - `list --stage inbox --all` exits 2.
   - A directory `notes/` in the work path, and a file `README.md`, do not
     appear and do not fail `list`.
   - One unreadable `item.yaml` makes `list` exit 1 naming that file.
   - **Tag filter.** With items A (`tags: [ui]`), B (`tags: [api, ui]`), C
     (`tags: [api]`) and D (no tags), all at request:
     - `list --tag ui` prints A and B only;
     - `list --tag ui --tag api` and `list --tag ui,api` each print A, B and
       C, and not D;
     - `list --tag nosuch` prints nothing and exits 0, including when
       `nosuch` is not in the tag registry;
     - `list --tag ui --all` also prints a completed item tagged `ui`, and
       `list --tag ui` without `--all` does not;
     - the `FsWorkBackend` contract case for `list(Query(tags={"ui"}))`
       returns the same items as `MemoryBackend` for the same data
       (criterion 1).
6. **Comments.**
   - `echo hi | tcw work comment <slug>` writes one file matching
     `comments/\d{8}T\d{6}Z\.md` containing `hi\n`, and prints nothing on stdout.
   - Two comments written with the clock fixed to the same second produce two
     files a second apart, with the first one's content unchanged.
   - An empty comment exits 2.
   - After three comments, `read_comments(folder, 2)` returns the two newest,
     each with `at` equal to the time in its file name, `author` `None`, and
     the file's text. A file `comments/notes.txt` is not returned.
7. **Trace.**
   - `advance --to plan --force --reason "skip"` from request (spec enabled)
     writes `stage: plan` and one comment file containing `skip`.
   - With `comments` made a plain file so the comment cannot be written,
     the same command exits 6, `item.yaml` says `plan`, and stderr says the
     trace was not recorded.
   - A `pre` hook on spec that writes `$PWD` and `$TCW_SLUG` to a file, run by
     `advance` from a subfolder of the project, records the project root and
     the full slug `<id>/<folder>`.
8. **Rename.**
   - In a fixture, items B (`parent: <id>/A`) and C (`blocked-by: [A]`, written
     bare) reference A. After `rename A new-words`:
     - stdout is the new slug;
     - A's folder has its old date and the new words;
     - B's and C's `item.yaml` name the new slug in full;
     - a line in A's `spec/spec.md` naming the old folder is reported on
       stderr as `path:line`;
     - there is no `renames.yaml`.
   - An item in a second project that names A is unchanged.
   - Renaming to an existing name exits 3. Renaming with `New Words` or with
     a different date prefix exits 2.
   - With an unreadable item in the project, rename exits 1 and A's folder is
     unchanged.
9. **Delegation.** Two projects, P and Q, are registered to each other.
   - `tcw work new "T" --project q`, run in P:
     - prints `q/<today>-t`;
     - creates Q's item at `inbox`;
     - stderr names the files and says they are uncommitted in Q's repository;
     - Q's `HEAD` and index are unchanged.
   - Each condition, broken in turn, exits 3 with a message naming it and
     writes nothing:
     - an unregistered ID;
     - Q declared in P's config but its checkout absent from this machine;
     - Q's work path removed;
     - an untracked file in Q's work store.
   - With Q's checkout absent, `tcw work show q/<folder>` run in P exits 5,
     and `show` of a slug whose project no declaration names exits 4.
   - `edit p-item --blocks q/<folder>` follows the same conditions, and on
     success adds `p/p-item` to that Q item's `blocked-by`.
   - A tag registered in P but not in Q exits 2.
10. **Removed commands.** Each of these, run as `tcw work <command>`, exits 2
    with the parser's unknown-command message, and writes nothing:
    - `start`, `submit`, `rework`, `complete`, `drop`, `delete`;
    - `inbox`, `tracker`, `tombstone`;
    - `reconcile`, `delegate`, `escalate`, `scaffold`;
    - `stage gate`, `stage validate`.

    `import tcw.tracker` raises `ModuleNotFoundError`. `tcw/work/jira/client.py`
    exists, and the moved transport tests in `tests/work/jira/test_client.py`
    pass.
11. **Streams and exits (installed).**
    - `edit` and `comment` print nothing on stdout.
    - `advance` and `discard` print exactly the new stage.
    - `path <slug> review --next` prints one absolute path ending
      `review/round-1.md` and nothing on stderr.
    - `path <slug> spec --handoff` prints one absolute path inside the item's
      `spec/` folder in TCW-69's handoff form, and writes no file.
      `--next --handoff` together exits 2.
    - An unknown slug exits 4.
    - A refused `advance` exits 3 with stdout empty.
    - `advance --dry-run` writes no file.
12. **No git state changes.** One test runs `new`, `edit`, `comment`,
    `advance --force`, `discard`, `rename`, a delegation and
    `edit --blocks` across P and Q. Before and after, it compares these in both
    repositories, and all are unchanged:
    - `git rev-parse HEAD`;
    - `git for-each-ref`;
    - `git ls-files --stage`.

    A second test scans `tcw/work/`, `tcw/validate.py`, `tcw/refs.py` and
    `tcw/capabilities/cli.py` and asserts that none of them runs git with a
    verb that writes: `add`, `commit`, `mv`, `rm`, `reset`, `checkout`, `merge`,
    `worktree add`, `worktree remove`, `push`, `pull`, `fetch`, `stash` or
    `tag`. It looks at git invocations (a `"git"` argument followed by the
    verb), not at bare words, so the moved Jira client in `tcw/work/jira/`,
    whose text uses words such as "add" and "comment" for HTTP calls, does not
    trip it. It is mutation-checked by adding a `git add` call.
13. **2.x names are gone.** No `.py` file under `tcw/` contains any of these
    strings:
    - `graveyard.yaml`, `dod.yaml`, `renames.yaml`, `state.yaml`,
      `tracker.yaml`;
    - `FsWorkStore`, `WORK_STATUSES`, `LIFECYCLE_STEPS`;
    - `tcw work ` followed by any verb from criterion 10 (for example
      `tcw work start`, `tcw work stage gate`).

    Checked by a test that greps the tree. The packaged prompt and procedure
    texts (`tcw/work/prompts/*.md`, `tcw/work/procedures/*.md`) are not `.py`
    files and are TCW-74's.
14. **No stage literals.** TCW-69's criterion 5 scan also covers
    `tcw/work/fs_backend.py`, `tcw/work/open.py` and `tcw/work/cli.py`, and
    passes. It is mutation-checked: adding `"request/request.md"` to
    `fs_backend.py` makes it fail.
15. **Validate.** Each fixture fault in Design 10.1 produces its line:
    - Errors make `tcw validate` exit 1.
    - A fixture whose only problems are a missing same-project blocker, a
      stage ahead of its artifacts, and an unregistered tag exits 0, reporting
      three warnings.
    - A reference into a project that is declared but whose checkout is absent
      is reported as unresolved and does not change the exit code. A reference
      into a project no declaration names is reported as a missing reference
      (a warning).
    - A directory `inbox/` in the work path is an error whose message names
      `docs/migration-guide-2.8-to-3.0.0.md`.
    - An item at `implement` whose `<item>/capabilities.yaml` has an unknown key
      fails.
    - Each line checked names its file (and key, where there is one). The
      test reads stdout and stderr together, so TCW-73 can move findings
      between streams without changing it.
16. **Drift.** In a fixture, a completed item declaring `new: [x/y]` while
    `x/y` is absent makes `tcw capabilities drift` exit non-zero and name
    `x/y`. Removing the declaration makes it exit 0. No `Planning doc` field is
    read.
17. **References.**
    - `tcw://W/<folder>` in a capability description passes `validate` when the
      item exists at any stage, including discarded.
    - It fails when the item does not exist.
    - `tcw://q/W/<folder>` resolves through Q.
18. **Init and provision.**
    - `tcw init --id p work` in an empty repository creates `docs/work/.gitkeep`,
      with no other entry under `docs/work`.
    - It adds no line to `.gitignore`.
    - `tcw provision` accepts a declared work repository whose store folder
      contains only item folders.
19. **Serve.** `GET /api/work` answers 404. The surviving taxonomy and
    capabilities route tests pass.
20. **Config.** In a fixture whose `tcw-config.yaml` has `work.tracker`,
    `tcw work list` exits 1, naming `work.tracker` and
    `docs/migration-guide-2.8-to-3.0.0.md` on stderr.
21. **Stage prompt.**
    - `stage prompt spec <slug>` composes the packaged `spec.md` with a
      `file:` binding from `work.stages.spec.prompt`.
    - `stage prompt review` exits 1, naming the missing
      `tcw/work/prompts/review.md`.
    - The output names no removed command.
    - A `generate:` binding receives the item record of 7.1 and runs with the
      project root as its working directory and `TCW_SLUG` the full slug.
22. **Documentation allowance.**
    - `tests/test_documented_cli_surface.py` passes with the temporary
      allowance.
    - The guard test fails if an entry that is still a real command is added
      to the command list, or a key `parse_work_config` accepts is added to
      the key list.
    - `DOCUMENTED_VERBS` names none of the commands in criterion 10.
    - The release-notes entry file's first non-blank line starts with `##`.
23. **Whole suite.**
    - `pytest` passes when run bare from the branch checkout, with this
      repository's `tcw-config.yaml` and board unchanged.
    - No test depends on the repository's own board or config: `pytest` also
      passes in a throwaway copy of the checkout from which the root
      `tcw-config.yaml` and `docs/work/` have been deleted. This is run once,
      by hand, and the result is recorded in the implement round.

### Coverage

| Design | Criteria |
| --- | --- |
| 1 Boundary | 10, 11 |
| 2 Opening | 9, 17, 20 |
| 3 Backend | 1–8, 11 |
| 4 Git, concurrency | 12 |
| 5 Rename | 8 |
| 6 Delegation | 9, 12 |
| 7 Commands | 2, 3, 5, 6, 11, 21 |
| 8 Config | 7, 20, 21 |
| 9 Deletion | 10, 13, 23 |
| 10 Validate, drift | 15, 16 |
| 11 Init, provision | 18 |
| 12 References, serve | 17, 19 |
| 13 Stage literals | 14 |
| 14 Documentation | 22 |
| 15 Testing | 1, 23 |

Atomic replacement of `item.yaml` (Design 3.2) is checked inside criterion 1 by
making the write fail after the temporary file is written: the old `item.yaml`
is intact.

## Risks

- **This is a large slice.** It writes a backend, rewires about a dozen commands
  and five surfaces, and deletes most of the work axis and about 110 test files.
  - Mitigation: the plan phases it so the suite is green after each phase:
    1. backend and contract tests, alongside 2.x;
    2. `open_backend` and the new commands, replacing the old ones;
    3. the rewired surfaces;
    4. deletion;
    5. records.
  - The owner decided on 2026-10-01 to keep it one item built in these phases,
    not child items: wiring and removal cannot land separately without a period
    where `tcw work` reads two layouts.
- **The epic branch has known gaps until later slices land.** `tcw serve` has no
  board, documents and skills name removed commands, and `stage prompt review`
  fails. Mitigation: each gap has a named owner, the documentation allowance
  makes one of them visible as a list, and nothing ships before 3.0.0.
- **One damaged `item.yaml` stops `list`** (Design 3.3). The failure is loud
  and names the file, git can restore it, and `validate` names the key. 2.x
  went the other way, degrading quietly, and this redesign set out to remove
  exactly that kind of hidden logic.
- **Concurrent edits on one machine can lose an update** (Design 4.6). This is
  rare, and it is the price of having no lock. If it proves real, a lock is an
  adapter detail that can be added without changing the interface.
- **A rename that fails midway leaves stale references.** Every one is then a
  `validate` warning naming it.
- **Ported tests can lose coverage silently.** Mitigation: the plan's
  per-file table states the fate of every test file. A surviving behavior's
  test is ported, and reviewers check the table, not only the diff.
- **TCW-69 is not implemented yet on this branch.** This spec relies on TCW-69's
  spec and plan. If its implementation changes a name or signature, the plan
  for this slice is re-read against it before work starts.

## Notes

- Reconciled with the epic's cross-slice decisions on 2026-10-01.
- **Decisions made in this spec**, each marked **[Decision]** above, for the
  owner to confirm:
  1. The boundary with TCW-73 is drawn by what the 2.x store made necessary.
     TCW-70 wires the item commands with TCW-73's stdout and exit codes and
     removes every store-built command (Design 1). The epic's decision 2
     accepted this split.
  2. `open_backend`, `open_project` and `open_delegation_target` are the single
     way in. Reading a project that is declared but not on this machine is
     exit 5 and delegating to one is exit 3 (the epic's decision 4); reading a
     project no declaration names is exit 4 (Design 2).
  3. The creation date is the local calendar date (3.1).
  4. `item.yaml` is rewritten whole, so hand comments are lost, and it is
     replaced in one step (3.2).
  5. Reading is strict. A bad stage value reads as "no stage" rather than
     unreadable (3.2).
  6. Piped text goes to the request document even for inbox items. There is no
     `intake.md` (3.3). This answers TCW-76's question of where an inbox
     item's text is stored.
  7. `list` fails on any unreadable item rather than hiding it (3.3).
     Settled by the owner on 2026-10-01: `list` fails on an unreadable
     `item.yaml`.
  8. A comment name collision moves to the next free second (3.3).
  9. `read_request` reads the request file rather than returning `None`, so
     callers never branch on the backend (3.3.9).
  10. `read_comments` ignores files whose names are not timestamps, and fails
      on a timestamp-named file it cannot read (3.3.10).
  11. `current_user` is implemented, but the backend is built with no
      `user_name` until TCW-72 supplies one (3.3.11).
  12. A work store is present when its directory exists (3.5).
  13. There is no lock (4.6).
  14. Rename takes only names already in folder form, works at any stage,
      searches only the work path for other mentions, and does not roll back
      (Design 5).
  15. Delegation reaches any project the registry locates, upstream projects
      included (6.2). Settled by the owner on 2026-10-01: delegation may write
      into the target's checkout after its three conditions pass. A store outside git fails the uncommitted-changes condition, and
      that check is a shared function TCW-71 also calls (6.3).
  16. `tcw work path` with no slug still prints the store folder (Design 7).
  17. Where TCW-73 still owns a command's output layout, this slice's tests
      check content and exit codes, not layout (Design 1).
  18. One item record, including `untracked`, serves `show --json`,
      `list --json` and `generate:` bindings; TCW-73 adds the envelope (7.1).
  19. A missing packaged prompt fails `stage prompt` with exit 1 (7.2).
  20. Tests go with their code, and surviving behavior's tests are ported.
      Tests whose subject a later slice rewrites (the skill-flow, prompt
      fallback and eval tests) are skipped with a reason naming that slice
      (Design 9).
  21. The Jira HTTP client, its fake and its transport tests are moved to
      `tcw/work/jira/` and `tests/work/jira/` rather than deleted, as TCW-71
      asked (Design 9).
  22. The item-folder checks are a function of the adapter module, not an
      interface operation (10.1).
  23. The "not part of a work store" messages always name the migration guide,
      with no code that recognizes 2.x (10.1).
  24. A reference into a project no declaration names is "missing", and one
      into a declared but absent project is "unresolved" (10.1).
  25. `validate` warnings and unresolved lines exit 0 (10.2).
  26. `tcw serve`'s 2.x work routes are removed, not ported (12.2). Settled by
      the owner on 2026-10-01: no `tcw serve` work pages between this slice
      and TCW-77.
  27. The no-stage-literals rule extends to the new modules (Design 13).
  28. Documentation beyond the changelog, release notes and records is
      deferred (Design 14).
  29. The capability and taxonomy dispositions in Capability changes. These
      include a new path for delegation, removing the start/submit/rework/
      complete records in favor of one `advance` record, and three new
      vocabulary terms.
  30. Settled by the owner on 2026-10-01: `tcw work list --tag` stays in
      3.0.0. This slice implements TCW-69's `Query.tags` over `item.yaml`
      tags, any given tag matching (3.3.3, Design 7, criterion 5).
- **Cross-slice findings, and how each was settled.** Nothing has been posted
  to any ticket.
  - TCW-69's spec counted one `work/` capability record; there are 46. Settled
    by the epic's decision 12: this slice decides each.
  - TCW-73's removal list, and the `validate` and `drift` wiring with the
    `detect-capability-drift` record, move to this slice. Settled by decision 2.
  - `tcw/work/templates.py` and `scaffold` are deleted here, not by TCW-74.
    Settled by decision 13.
  - `spec/capabilities.yaml` in older ticket text. Settled by decision 19:
    `<item>/capabilities.yaml` everywhere.
  - Migrated verdict rounds need `judges:`. TCW-76's spec now writes
    `judges: 1` into every converted verdict round, so this is settled there.
  - TCW-77 starts from a server with no work routes and builds on the item
    record (7.1). TCW-77's spec agrees. Its `record()` operation is replaced by
    `read_request` and `read_comments` (decision 1).
  - TCW-71's four seams (`jira` branches of `open_backend` and
    `open_delegation_target`, Jira projects through `open_project`, a third
    contract-test parameter) stay as written. Its request to move the client
    and fake is accepted (this spec's Decision 21); its request for a callable
    uncommitted-changes check is accepted (this spec's Decision 15). The strict
    `item.yaml` reader belongs to the filesystem adapter alone.
  - TCW-72's `me()` is replaced by `current_user()` (decisions 1 and 17). A
    comment author in filesystem mode stays TCW-72's to add, for example as
    front matter in the comment file.
  - `evals/` goes to TCW-74 and `tests/cli/scenarios/` to TCW-73. Settled by
    decision 14.
  - The temporary documentation allowance must be empty before 3.0.0 is cut,
    checked by TCW-76's "validate clean" step. Settled by decision 6, which
    also replaces TCW-75's "smallest edit" proposal.
  - Exit 4 or 5 for a project declared but not on this machine (TCW-73's
    draft said 4). Settled by decision 4: exit 5.
  - TCW-73 renames the config key `connected-projects:` to `projects:`
    (owner answer of 2026-10-01). This slice reads the key under its current
    name through `tcw/store/project.py`; the rename and its effect on
    Design 2 are TCW-73's.
  - Exception classes live in `tcw/errors.py` (decision 8). TCW-73's draft
    still names `tcw/work/errors.py`.
- **Open questions only the owner can answer:**
  1. Settled by the owner on 2026-10-01: TCW-70 stays one item, built in the
     five phases under Risks.
- **The ticket's own open questions.** The ticket lists none. The questions this
  spec answers are the ones its scope raised: the boundary with TCW-73
  (Design 1), how it is tested while the board is 2.x (Design 15), and which
  surfaces are rewired rather than removed (Designs 10–12).
- **Assumption, not grounded in code:** TCW-69's implementation follows its
  spec and plan, as revised for the epic's decisions (module names
  `model.py`, `layout.py`, `backend.py`, `advance.py`, `gates.py`,
  `references.py`, `config.py`, and `tcw/errors.py`, `tcw/exit.py`; eleven
  backend operations; TCW-69's `Comment` type and the order `read_comments`
  returns). None of them exists on this branch yet. If TCW-69's revised spec
  defines any of these differently, it wins.
- **Driving this item.** This item's implementation edits `tcw/`, and it is the
  slice after which the branch's CLI cannot read this repository at all. From
  implement onward, the board is driven by editing files (Design 15.3), and
  this item's Jira ticket is moved by hand (the epic's decision 7).
