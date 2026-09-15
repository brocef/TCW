# Plan — Inherit work.tracker from parent nodes, key by key

Implements `spec.md` (the version revised after review, where inheritance is
opt-in, and amended after the plan review). Criterion numbers (C1–C26) refer
to its Acceptance criteria.

## Before starting

- Start with
  `tcw work start 2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key --worktree`.
  The work edits `tcw/`, so it runs in `.worktrees/<slug>/`. Re-point the
  editable install with `pip install -e <worktree> --no-deps`, and run pytest
  and the CLI with the worktree root as the current directory (`CLAUDE.md`,
  "Working in a `--worktree` branch"). Restore the install with
  `pip install -e /Users/brian/Projects/TCW` before `tcw work complete`, and
  run that from the primary checkout.
- **Every task from Task 1 on runs inside the worktree** and commits to the
  work branch. That includes the capability record and the documentation.
  Nothing from this plan is committed to `main` directly.
- **Relation to the claim item**
  (`2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`,
  implementing in its own worktree since `de5a8da8`). Its spec (Risks 6) adds
  no configuration key and reads settings only through `tracker_config()`, so
  neither item blocks the other and no blocker is recorded. Both will edit
  `README.md`, `skills/tcw-work/references/commands.md`, `docs/guide/work.md`
  ("Reading an external tracker") and the two `upcoming.md` files. Whichever
  merges second resolves those text conflicts. If both ship in one release,
  review their combined change as well (`CLAUDE.md`, Reviews).

## Tasks

### Task 1 — Capability record and sidecar

Run these inside the worktree, with the install re-pointed at it, before any
`tcw/` edit:

```sh
tcw capabilities add work/inherit-tracker-settings-from-parent-nodes "Inherit tracker settings from parent nodes" --status Missing
tcw capabilities set work/inherit-tracker-settings-from-parent-nodes --field Feature=external-work-tracker --field "Planning doc=2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key" --field Subject=cli,reference
```

This creates `docs/capabilities/work/inherit-tracker-settings-from-parent-nodes/meta.yaml`
and `description.md`. The description is written in Task 6.

**Creates** `docs/work/active/2026-09-14-inherit-work-tracker-from-parent-nodes-key-by-key/capabilities.yaml`
in the worktree, in the same form as the initiative's sidecar:

```yaml
new:
    - work/inherit-tracker-settings-from-parent-nodes
```

**Proves:** `tcw capabilities check` and `tcw validate` pass,
`tcw capabilities show work/inherit-tracker-settings-from-parent-nodes` shows
Status Missing, and `ls` shows both `meta.yaml` and `description.md` (the
check passes on a `description.md` without `meta.yaml`, so it does not prove
this alone). Commit on the work branch.

### Task 2 — Pure merge, credential check and attribution

**Modifies** `tcw/store/base.py`: `parse_tracker_config` (`:907-1004`), and
new functions directly after it. **Creates** `tests/test_tracker_inheritance.py`.

First, the parser fix (Goal 8): change `sorted(set(raw) - TRACKER_KEYS)`
(`:929`) and `sorted(set(value) - allowed)` (`:960`) to sort with `key=str`.
Nothing else in the parser changes.

Then add three functions. None of them reads a file or the environment. Key
paths in the source record are tuples of `str(key)`, so an integer key cannot
break sorting or joining.

1. `merge_tracker_blocks(blocks: list[tuple[str, Any]]) -> tuple[Any, dict[tuple[str, ...], str], str | None]`
   - `blocks` is nearest first, as `(label, raw)` pairs. The first entry is
     the node itself, and the caller only passes ancestors when the first
     entry is a non-empty mapping (spec Design, "Which blocks take part").
   - Skip ancestor entries whose raw value is `None` or `{}`.
   - At the first ancestor entry that is not a mapping, stop and return
     `(raw, {}, label)`. The third value is the label that owns a whole-block
     problem, and it is `None` otherwise.
   - Lay mappings from farthest to nearest, recursing for mapping-over-mapping
     and replacing otherwise. A `None` value in a nearer block does not
     replace a value already there, **and does not touch the source record**
     for that path or anything under it. A `None` with nothing below it is
     kept and recorded against the block that wrote it, so a problem about it
     names that file.
   - When a nearer non-mapping replaces a mapping (or the reverse), remove
     every record entry under the replaced path before recording the new one.
   - Deep-copy each block before laying it
     (`copy.deepcopy`, since `FsProjectRegistry.config()` returns a shallow
     copy).
   - The source record maps each key path in the result to the label that
     supplied its value. A nested mapping's own path maps to the nearest
     label that contributed to it. Attribution looks up exact paths only
     (see function 3), so that entry is never used to blame an unset key
     beneath it.
2. `tracker_credentials_problem(provenance, labels_nearest_first) -> str | None`
   - Finds the index (in nearest-first order) of the label that supplied
     `("base-url",)` and the largest index among labels that supplied any
     `("credentials", …)` path. If both exist and the credentials index is
     larger, return
     `f"work.tracker.credentials: inherited from a parent node, but base-url is set nearer, in {base_url_label}; set credentials in the same file as base-url"`.
3. `attribute_tracker_problems(problems, provenance, own_label, whole_block_label) -> list[str]`
   - A problem equal to `work.tracker: expected a mapping, …` goes to
     `whole_block_label` when set, and to `own_label` otherwise.
   - Otherwise, take the text between `work.tracker.` and the first `: `, and
     look for a record path whose parts joined with `.` equal it **exactly**.
     With a match, use that path's label. With no match, use `own_label`: that
     is a key nobody set, including a nested required key under a mapping an
     ancestor supplied (spec C22). Exact matching on the joined string is what
     makes a key literally named `a.b` resolve (C24).
   - Return `f"{label}: {problem}"`, keeping the parser's sorted order.

**Tests (written first)**, from an empty `tmp_path` as the current directory:

- C18: criterion 4's mappings; the result and the two source entries.
- C6 and C7 at merge level: a nearer null keeps the farther value, and a lone
  null survives.
- A list replaces rather than concatenating. A mapping over a string replaces.
- A non-mapping ancestor stops the merge and returns its label.
- The inputs are not mutated. Deep-compare them before and after.
- Record after a skipped null: nearer `credentials: {email-env: null, token-env: null}`
  over a farther mapping records both sub-paths against the farther label
  (the merge half of C23). Nearer `credentials: null` does the same.
- Record after wholesale replacement: nearer `credentials: "x"` over a farther
  mapping leaves no `("credentials", …)` sub-path entries.
- Credentials: `base-url` nearer than `credentials` → message. Only
  `credentials` nearer → `None`. Both from the same label → `None`.
  `token-env` nearer but `email-env` from farther than `base-url` → message.
  `base-url` nearer with credentials all-null nearer → message (C23).
- Attribution, one case for each parser message shape: unknown top-level key,
  unknown nested key (`credentials.x`), wrong type, unsupported provider,
  missing top-level required key (own label), missing nested required key
  under an ancestor's mapping (own label, C22), unknown key named `a.b` from an
  ancestor (ancestor label, C24), and whole block not a mapping.
- C26: `parse_tracker_config` with unknown keys `5` and `z` at the top level,
  and again inside `credentials`, returns both problems and does not raise.

**Proves:** the new tests pass, and `tests/test_tracker_config.py` passes
unchanged. Confirm C26's test fails before the `key=str` change and passes
after it. Commit.

### Task 3 — The filesystem store reads through the ancestors

**Modifies** `tcw/store/fs.py`: `tracker_config` and `tracker_problems`
(`:5284-5295`), plus one private helper beside them.

`_resolved_tracker(self) -> tuple[TrackerConfig | None, list[str]]` holds the
whole flow. Both public methods call it, so they cannot disagree:

1. `own = self._work_config().get("tracker")`. If `own is None or own == {}`,
   return `(None, [])`. If `own` is not a mapping, return
   `parse_tracker_config(own)` with problems prefixed `f"{SENTINEL}: "`
   (today's behavior).
2. Build `blocks = [(SENTINEL, own)]`. In a `try`, open
   `FsProjectRegistry.open(self.node_root)` and call `require_valid()`. On
   `ValueError`, skip to step 4 with the node's own block only.
3. For each `ancestor` in `registry.ancestors()`, take
   `work = registry.config(ancestor.id).get("work")`. When it is a mapping,
   append `(f"{Path(ancestor.locator) / SENTINEL} (project '{ancestor.id}')", work.get("tracker"))`.
   Then find an unreachable ancestor: `last = ancestors[-1].id if ancestors else None`,
   `pid = registry.declared_parent_id(last)`, unreachable if `pid` is set and
   `registry.get(pid) is None`.
4. Merge. Parse the merged result. If it parses cleanly, run the credential
   check. A message from that check becomes a problem at `SENTINEL`, and the
   config is dropped.
5. Attribute problems. If any exist and an unreachable id was found, append
   the notice from spec Design, "Ancestors this checkout does not have".
6. Return `(config or None, problems)`.

`WorkStore` in `base.py` is untouched: same signatures, same defaults.

**Tests (written first)**, in `tests/test_tracker_inheritance.py`. Nodes with
a board are made with `init(["work"], path, id)` and nodes without one with
`write_sentinel(path, id)`. Graphs are joined with a local `connect()` copied
from `tests/test_store_nodes.py:21-31`, and each node's `work.tracker` is
written with `yaml.safe_dump` **after** connecting (`connect()` rewrites the
file).

**Fixture rules**, because a broken graph makes the store quietly fall back to
the node's own block, and a test could then pass for the wrong reason:

- Connect top-down: `connect(root, repo, …)` before `connect(repo, pkg, …)`.
  `connect()` replaces the child's whole `connected-projects`, so the other
  order wipes repo's `children` and the graph becomes non-reciprocal.
- The fixture helper asserts `FsProjectRegistry.open(node).check() == []` for
  every node before a test uses the graph. The C13/C14 fixtures assert it
  before deleting.
- Project ids avoid the reserved single letters `c`, `t` and `w`. Use
  `root`, `repo`, `pkg`, and `aa` / `bb` for the cycle.

**Tests:**

- C1–C11, C13–C16, C22, C23, C24 and C25 through
  `FsWorkStore.open(<node>).tracker_config()` and `.tracker_problems()`, with
  the exact strings the spec gives. `<root config absolute path>` is
  `str(root_path.resolve() / "tcw-config.yaml")`.
- C3's validate part: run `tcw validate` in-process at root (as `_run` in
  `tests/test_tracker_cli.py` runs commands) and assert it exits 0 and prints
  `validate OK`.
- C13: build root → repo → pkg, connect top-down, check the graph, then
  `shutil.rmtree(root)`. Pkg's problems include the two exact lines.
- C14: build the same graph, check it, then `shutil.rmtree(repo)`. The notice
  names `repo`.
- A graph with a cycle (`aa` ↔ `bb`), opened directly through
  `FsWorkStore.open(aa)`: `tracker_config()` does not raise and uses `aa`'s own
  block.

**Proves:** new tests pass, and the four existing tracker test files pass
unchanged (C12). Commit.

### Task 4 — CLI end to end

**Modifies** `tests/test_tracker_inheritance.py` only. `_tracker_client`
(`tcw/work/cli.py:1607-1631`) already reads through `tracker_config` and
`tracker_problems`, so no CLI code changes.

- C17: criterion 1's graph. Chdir to pkg, set the credential environment
  variables, and replace `jira.JiraClient._request` with a fake that records
  `self.config.base_url` and the request (as `tests/test_tracker_cli.py:94-101`
  does). Run `tcw work tracker list` in-process. It exits 0, and the recorded
  call has root's `base-url` and pkg's query.
- `tcw validate` at root, with root's block holding `base-url: 42` and pkg
  opting in: exits 1. The problem line carries pkg's `[pkg]` prefix and root's
  config path (spec Design, "Validation across child nodes").

**Proves:** the tests pass. Commit.

### Task 5 — Full suite

Run `python -m pytest` and bare `pytest` (what CI runs) from the worktree root,
in the background, since the suite takes about 13 minutes. Both must pass
(C19). No commit: nothing changes here. A failure goes back to the task that
caused it.

### Task 6 — Documentation Sync (one pass over the finished diff)

Every documentation entry, evaluated:

- **`README.md` [Public-API] — fires.** In the tracker section, next to the
  config example (`README.md:372`), add a short paragraph and a two-node
  example: a child block holding only `candidate-query` takes its other
  settings from parent nodes, the nearest file wins each key, a node with no
  block has no tracker, and `credentials` must sit with `base-url` (even when
  the `base-url` value repeats the parent's). Add one sentence on the limit:
  a node with its own board that holds shared settings is checked like any
  tracking node, so it needs a `candidate-query` of its own (C20).
- **`docs/release-notes/upcoming.md` [Public-API] — fires.** A plain-language
  entry covering what a workspace can now write once, and that nodes without a
  tracker block are unaffected.
- **`docs/changelogs/upcoming.md` [Any-Code-Change] — fires.**
  - "Added": the merge in `tcw/store/base.py`, the credentials check, problems
    naming the ancestor file, and the unreachable-ancestor notice.
  - "Changed": a node's own `null` value now takes an ancestor's value when
    one exists (spec Risks 5), and a partial child block is rejected by v2.1.x
    (spec Risks 3).
  - "Fixed": `parse_tracker_config` no longer raises on a block mixing string
    and non-string keys (spec Goal 8).
- **`skills/<component>/SKILL.md` [Skill-Driven-Component] — fires for
  `tcw-work`**, because the work component's configuration changes.
  `skills/tcw-work/SKILL.md` does not mention the tracker, so the update goes
  in the reference it points to, `skills/tcw-work/references/commands.md`,
  under "Reading an external tracker" (line 83). Cover the opt-in rule, the
  credentials rule (including the repeated-`base-url` case), the
  board-holding-parent limit (C20), and how to read a problem that names a
  parent's file.
- **Not a documentation entry, but covered by C20:** `docs/guide/work.md`
  "Reading an external tracker" (line 605) gets the full rule. That includes
  the board-holding-parent limit (spec Non-goals), no way to unset an
  inherited key, and the unreachable-ancestor notice.
- **Capability text (C21).** Write
  `docs/capabilities/work/inherit-tracker-settings-from-parent-nodes/description.md`
  in the "As a developer…" form used by `inspect-external-tracker-work`. Add
  one sentence to `docs/capabilities/work/inspect-external-tracker-work/description.md`
  saying these settings may come partly from parent nodes.

**Proves:** `tcw validate` and `tcw capabilities check` pass. The README and
guide examples, written into a scratch graph, give what the text says. Commit.

### Task 7 — Outcome

Write `outcome.md`: what was built, any departure from the spec or this plan,
the suite results, and the commit list. The capability stays Missing until
`verify` accepts the work and flips it, as on the configure item. The sidecar
then lets `complete` go ahead.

Record that GitHub issue #36 stays open. `CLAUDE.md` holds closing an
originating issue until the fix is released and pushed, and the reply text
needs the user's approval first. `refined-outcome.md` repeats this at
`verify`. Commit on the work branch.

## Coverage check

| Criterion | Task |
| --- | --- |
| C1–C5, C8–C11, C13–C16 | 3 |
| C6, C7 | 2 (merge level), 3 (store level) |
| C12 | 2, 3 |
| C17 | 4 |
| C18 | 2 |
| C19 | 5 |
| C20 | 6 |
| C21 | 1, 6 |
| C22, C23, C24 | 2 (merge and attribution), 3 (store level) |
| C25 | 3 |
| C26 | 2 |

## Documentation Sync

See Task 6. All four entries fire: `README.md`,
`docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, and the
`tcw-work` skill through `skills/tcw-work/references/commands.md`.

## Verification

What the suite cannot check:

- **A real Jira site.** Every tracker test fakes `_request`. For the verifier,
  optionally: build a scratch graph of a board-less root holding everything but
  `candidate-query`, a repo with a board and no block, and a pkg holding only
  `candidate-query`. Run `tcw work tracker list` at pkg against the
  requester's real site, with credentials in the environment. It should list
  pkg's slice. At repo it should say no tracker is configured, and
  `tcw validate` at root should pass.
- **The requester's own six-node workspace.** Reduce each child block to its
  `candidate-query`, then run `tcw validate` at the workspace root. It should
  pass, and `tcw work tracker list` in each package should match what it
  listed before the change.
- **The docs read clearly.** Someone who has not read the spec should be able
  to tell from `docs/guide/work.md` alone what a node with no tracker block
  gets, and why a `base-url` change needs `credentials` beside it.
