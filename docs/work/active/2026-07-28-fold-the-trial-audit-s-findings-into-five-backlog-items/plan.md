# Plan: Fold the trial audit's findings into five backlog items

Nine tasks. Task 1 is the only code change and comes first because task 5 uses
the flag it adds. Tasks 2–5 are independent of each other. Tasks 6–9 are the
Documentation Sync block, scheduled together at the end over the finished diff.

## 1. Add `--title` to `tcw work edit`

**Changes** `tcw/work/cli.py`:

- `pe.add_argument("--title", type=_nonempty, help="set the item title")` on the
  `edit` subparser (`cli.py:998-1014`).
- `title=_provided(args.title)` in the `st.update_work(...)` call
  (`cli.py:705-712`).
- A `_nonempty` argparse `type=` validator beside `_work_level` (`cli.py:35-41`),
  which is the existing precedent for validating at the argparse boundary.
  It needs no `None` branch: argparse calls `type=` only on a value actually
  present on the command line, so an omitted `--title` leaves `args.title` at
  `None` and `_provided` turns that into `_UNSET`.

**Why the validator.** `_provided` maps only `None` → `_UNSET` (`cli.py:197-200`),
so `--title ""` reaches `update_work`, which writes `state["title"] = ""`
(`fs.py:2588-2590`) and leaves an item with no title. `create_work` refuses an
empty title (`fs.py:2422-2423`); `edit` must refuse it too, or the CLI offers a
way to reach a state the constructor forbids. Rejecting at the parser keeps the
store unchanged.

**Also** fix the `edit` subparser's help string, currently "change blocking links
between items" (`cli.py:998`) — already wrong, since `edit` sets priority,
estimates, initiative, and tags. `--title` makes it wronger. One string, in the
line this task already edits.

**Verified by** a new test in `tests/test_work.py` beside the existing
`test_cli_edit_*` cases (`tests/test_work.py:826-843`):

- retitle via the CLI → `get_detail` reports the new title and the **unchanged**
  slug (the stable-ID guarantee the capability claims);
- `--title ""` exits non-zero and leaves the title untouched;
- a retitle leaves `initial-request.md` byte-identical (the store writes the body
  only when `body` is passed, `fs.py:2624-2626` — the capability promises this,
  so it gets a check rather than a comment).

Run: `pytest tests/test_work.py -q`.

## 2. Fold findings into `2026-07-03-transactional-multi-file-writes-in-the-fs-store`

**Changes** that item's `initial-request.md`. Adds:

- `FsWorkStore.create` (`fs.py:2288-2295`) as a fourth unprotected write site —
  plain `write_text` + `dump_yaml`, not even `_atomic_write`; declared abstract at
  `base.py:931`.
- The corrected caller claim: no caller under `tcw/`; `.create(` appears across 17
  test modules, every one of which builds an `FsWorkStore`. Collapsing it into
  `create_work` stays an option, priced as a test-surface migration.
- ~~The `create_work` gap~~ — **dropped during implementation.** The item already
  names `create_work` in its Problem section; the spec proposed it as new without
  re-reading the target. See the withdrawn finding in `spec.md`.
- `accept_inbox` (`fs.py:2246-2269`) as the in-repo precedent to copy — `mkdtemp`
  → populate → `os.replace` → `rmtree` on except — so the implementer extends a
  pattern instead of designing a helper.

**Verified by** reading the item back: each citation opened and confirmed to show
the claimed code. No test covers prose.

## 3. Fold findings into `2026-06-22-concurrency-safe-work-claims-…`

**Changes** that item's `initial-request.md`. This one **corrects the item's own
text**, so the edits land at the claims they correct, not in a footer:

- At `initial-request.md:42-43` ("`FsWorkStore` already takes `root` as a
  parameter, so this is the only new branching"): `FsTreeStore.__init__` derives
  `node_root = root.parent.parent` (`fs.py:578-585`), and `node_root` is what git
  operations (`fs.py:261-349`), the sentinel reader (`fs.py:85`, `110-127`), and
  hook cwd (`work/hooks.py:61`) key off — including the sentinel that would hold
  `work.path` itself, making it config-reads-config.
- At the `--force` proposal: `start --force` already exists with different
  semantics — "start despite unresolved blockers" (`cli.py:973`) — so the
  take-over flag needs another name. Record the collision, **do not pick the
  replacement name**: naming a flag on that item's own CLI surface is its spec's
  call, and choosing it here is exactly the silent scope-widening this item's
  acceptance criteria forbid.
- At the "stamps the winner *after* the move" line: the move is now committed
  inside `_effect_transition` (`fs.py:2321-2322` → `_commit_transition`), so a
  post-move stamp lands as a second commit rather than riding the transition.

**Verified by** citation read-back, as task 2.

## 4. Fold findings into `2026-07-01-transitive-taxonomy-inheritance`

**Changes** that item's `initial-request.md`. Adds:

- `Term.origin` is a single alias (`base.py:152`) used directly as a dict key
  (`fs.py:863`, `fs.py:893`), so a two-hop origin has no representable value
  today — the encoding is a decision that item's spec must make.
- Cycles are already guarded at any depth — the `_seen` set threaded through
  nested store construction (`fs.py:656-664`) and `_cycles` (`fs.py:868-884`) —
  so guarding them is **out of** that item's scope.
- A link to `taxonomy/federate-shared-vocabulary`, whose `Gaps` line already names
  "transitive (multi-level) extends" as deferred.

**Verified by** citation read-back, plus `tcw capabilities show
taxonomy/federate-shared-vocabulary` confirming the Gaps wording is still there.

## 5. Retitle `2026-07-02-add-a-vendored-rich-markdown-editor-…`

**Changes**, in this order:

- `tcw work edit 2026-07-02-add-a-vendored-rich-markdown-editor-to-the-local-web-app
  --title "Add a rich Markdown editor to the local web app"` — using the task-1
  flag, which is the point of adding it.
- That item's `initial-request.md`: the `# ` heading (the store does not touch it),
  and the `> **Title note:**` at lines 3–6, which currently explains why the title
  says "vendored". After the retitle it should explain only why the **slug** does —
  the part that stays true.

**Verified by** `tcw work show <slug>` reporting the new title and the old slug,
and `git diff` on the item showing the H1 and note changed together.

## Documentation Sync

Evaluated against `CLAUDE.md`. All four entries fire — task 1 changes the public
CLI surface, and it is a behavior-affecting change to the work component.

### 6. `README.md` [Public-API]

Add `--title` to the `tcw work edit` block at `README.md:597-603`, matching the
existing one-line-per-flag comment style.

### 7. `docs/changelogs/upcoming.md` [Any-Code-Change]

Under **Added**: the `--title` flag, the empty-title rejection, and the corrected
`edit` help string. Technical register; name `_edit`/`update_work`.

### 8. `docs/release-notes/upcoming.md` [Public-API]

Plain language: you can now rename a work item from the command line, and the
item's ID does not change when you do. No module names.

### 9. `skills/tcw-work/references/commands.md` [Skill-Driven-Component]

The work component's CLI surface changed, so its driving skill must follow. The
command table's edit rows are `commands.md:17-18`; `--title` needs a row. Check
`skills/tcw-work/SKILL.md` in the same pass — if the router mentions no edit
flags, it needs no change, and that is a finding to state, not a silent skip.

## Verification

Beyond `pytest`:

- **`tcw validate`** — the four edited items and the new capability folder are
  node content; this catches malformed YAML and dangling `tcw://` links that the
  Python suite never sees.
- **`tcw capabilities check`** — must stay clean with `work/retitle-a-work-item`
  present.
- **Citation read-back (manual).** The suite cannot check that `fs.py:2288-2295`
  still shows what tasks 2–4 claim it shows. Every file:line written into a target
  item gets opened and confirmed against the tree at the end of implementation.
  This is the item's central acceptance criterion and it has no automated proxy —
  the trial run being wrong twice is exactly why.
- **Scope read-back (manual).** Re-read each target item's diff and confirm no
  goal was added or removed, only claims and citations.
- **Capability flip** — `work/retitle-a-work-item` goes `Missing` → `Supported` at
  closeout; the completion gate blocks otherwise.

## Notes

- No blockers to record with `tcw work edit --blocked-by`: nothing outside this
  item gates it, and the internal ordering (1 before 5) is a task order, not an
  item dependency.
- Tasks 2, 3, and 4 touch three disjoint files and share no state — dispatchable
  in parallel if useful. Task 5 must follow task 1.
- Task 3 is the one with real judgment in it: it rewrites claims inside an item
  whose author reasoned from them. Corrections state what the code does and let
  that item's spec decide what follows; they do not redesign its approach.
