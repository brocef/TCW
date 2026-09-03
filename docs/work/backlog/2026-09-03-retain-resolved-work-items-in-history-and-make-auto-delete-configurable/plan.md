# Plan — Retain resolved work items in history, and make auto-delete configurable

## Tasks

### 1. Parse and validate `work.retain`

**Modifies** `tcw/store/base.py`, `tcw/validate.py`.

Add a pure parser beside `parse_repository_declaration` and
`parse_documentation_entries` (`tcw/store/base.py:1191`, `:1261`) — same shape:
touches no filesystem, never raises, returns `(value, problems)`. It reads
`work.retain` as a mapping of resolved status to boolean, defaulting every
`RESOLVED_STATUSES` member (`tcw/store/base.py:488`) to `True`.

Unknown keys, non-boolean values, and a non-mapping `retain` are problems naming
the line. Unlike the repository parser this one does **not** fail closed to
"nothing declared": a malformed retention setting must not silently read as the
default, because the default and the mistake differ by whether files are deleted.
Return the safe value (`True`) *and* the problem, and have `tcw validate` surface
it.

**Proves it:** `tests/test_lifecycle_validation.py` — every malformed shape
reports its own message; an absent `retain` yields `True` for both statuses; a
valid partial mapping defaults only the unnamed status.

### 2. Report the retain/gitignore conflict

**Modifies** `tcw/validate.py`.

Where `retain` is `True` for a status whose folder is gitignored — the state
every existing project is in the moment it declares retention — report it: the
project says retain, git says otherwise, and the resolved items will not be
tracked. `git_ignored` (`tcw/store/fs.py`) already answers the question and
`resolved_ignore_rules` (`:720-731`) names the lines.

This is a report, not a refusal. A project mid-migration is legitimately in this
state.

**Proves it:** `tests/test_validate.py` — a node with the default rules and no
declaration is silent (that is today's setup and must not start warning); the
same node declaring `retain: true` reports the conflict; the same node with the
rules removed is silent.

### 3. Refuse auto-delete while the destination is gitignored

**Modifies** `tcw/store/fs.py`.

Before any move, a resolving transition whose target status has `retain: false`
checks `git_ignored` on the destination and refuses if it is ignored, naming the
`.gitignore` lines to remove and the config key that asked for deletion.

This lands **before** task 4 deliberately: the spec's sharpest finding is that
auto-delete over the ignore rules destroys the item, and no intermediate commit
of this plan may make that reachable.

**Proves it:** `tests/test_repo_lifecycle.py` — with the rules present and
`retain: false`, `tcw work complete` exits non-zero, the item is still in
`active`, and nothing is committed. With the rules removed it proceeds.

### 4. Record the retrieval handle on the tombstone

**Modifies** `tcw/store/base.py`, `tcw/store/fs.py`.

Add an opaque `location` field to `Tombstone` and to the graveyard entry written
by `_write_tombstone` (`tcw/store/fs.py:3833-3866`), documented as presentation
only and never parsed — the rule `ProvisionResult.location` already states
(`tcw/store/base.py:729-739`). The filesystem adapter writes the commit SHA the
item was last present in; another adapter writes whatever its own retrieval
handle is.

Absent on every existing entry, so readers must tolerate its absence and say
nothing rather than inventing one.

**Proves it:** `tests/test_repo_lifecycle.py` — a graveyard entry written before
this field still loads and reports no location; a new entry under `retain: true`
records the resolving commit; `yaml.safe_load` of the file shows sorted keys and
one added block, preserving the diff property `_write_tombstone`'s docstring
relies on.

### 5. The second commit

**Modifies** `tcw/store/fs.py`.

Under `retain: false` for the destination status, a resolving transition:

1. moves and commits as it does today, with the graveyard write **inside** that
   commit, carrying the SHA once it is known (write the entry, amend or write the
   SHA in the same commit — whichever keeps a single commit containing both the
   item and its record);
2. deletes the item folder and commits the removal;
3. publishes, if the store publishes, after the second commit.

A run that finds an item already recorded in the graveyard and still present in
its resolved folder — the crash window — completes step 2 rather than erroring.

**Proves it:** `tests/test_repo_lifecycle.py` — two commits, the first containing
the item's files under the resolved folder and the second removing them;
`git show <recorded sha>:<path>` retrieves `spec.md`; the folder is gone from
disk; re-running after an interrupted step 2 finishes cleanly.

### 6. Publication carries both commits

**Modifies** `tcw/store/fs.py`.

`publish` (`:4192-4212`) pushes the branch after the transition. Confirm the push
runs after the *second* commit and that the "your work is saved here" failure
message (`:4239-4250`) still names a true location when the push fails between
them. Read-and-assert unless the ordering is wrong.

**Proves it:** `tests/test_external_work_store.py` — against a local bare
repository, a provisioned store completing an item under `retain: false` leaves
the remote holding both commits; a push failure leaves both locally and exits
non-zero.

### 7. `tcw work show` answers from the tombstone

**Modifies** `tcw/work/cli.py`.

A slug that resolves only to a tombstone reports the resolution, the date, and
the recorded location where present — instead of reporting nothing. The existing
tombstone fallback (`tcw/store/fs.py:333-343`) is where the record already
arrives; this is the presentation half.

**Proves it:** `tests/cli` — `tcw work show <auto-deleted slug>` prints the
resolution and the SHA; a slug that names nothing at all still reports that.

### 8. Stop scaffolding the ignore rules against a declared retention

**Modifies** `tcw/store/fs.py`.

`init` writes `resolved_ignore_rules` unconditionally (`:903`). When the config
being initialized declares `retain` for a status, do not write that status's
rules. A project declaring nothing keeps today's scaffolding, which is what keeps
criterion 1 true.

**Proves it:** `tests/test_scaffold.py` — `tcw work init` on a config declaring
`retain: true` writes no rules for that status; on a config declaring nothing it
writes both, byte-identical to today.

### 9. Documentation Sync

One pass over the finished diff.

- **`README.md`** — [Public-API]. Fires. The resolved-work section
  (`README.md:190-199`) documents the gitignore rules as the mechanism. It gains
  the three modes, the default, the interlock, and the migration order: back-fill
  the graveyard with `tcw work tombstone add`, remove the rules,
  `git rm -r --cached`, then declare `retain`.
- **`docs/release-notes/upcoming.md`** — [Public-API]. Fires. Plain language: you
  choose what happens to finished work; nothing is deleted unless you ask; when
  you do, it stays in the repository's history.
- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Added:
  `work.retain`, the second commit, the tombstone location field. Changed: `init`
  scaffolding, `tcw work show` on a resolved slug, `tcw validate`.
- **`skills/<component>/SKILL.md`** — [Skill-Driven-Component]. Fires for
  `tcw-work`: `references/transitions.md` describes what a resolving transition
  does and `references/commands.md` documents `tcw work tombstone add`. Both need
  the two-commit path and the migration order.
- **`docs/capabilities/work/keep-resolved-work-out-of-git/`** — recorded as
  changed in `capabilities.yaml`; its body calls the gitignore mechanic "the
  default" and that is no longer the whole picture. Check
  `work/complete-a-work-item` and `work/discard-a-work-item` in the same pass and
  add them to the sidecar if their bodies describe the folder's fate.

## Verification

What the suite cannot check:

- **That the content is really retrievable.** After implementing, complete a
  throwaway item in this repository under `retain: false`, then recover its
  `spec.md` from the recorded SHA in a *fresh clone* — not the working checkout,
  which could satisfy the check from disk. Paste both commands and their output
  into `outcome.md`.
- **The migration on a real board.** The `proposit-*` stores have no
  `graveyard.yaml` and years of untracked `completed/` folders. Walk the
  documented migration on a copy of one and confirm the order in the README is
  correct and sufficient. Do not perform it on the real store as part of this
  item.
- **That the default is genuinely inert.** Run the full suite with no `retain`
  declared anywhere and confirm no resolution test changed its expected commit
  count. Criterion 1 is the promise every existing user is relying on.

## Notes

Task order is chosen so that no commit of this plan can produce a contentless
deletion: the refusal (task 3) exists before the deletion path (task 5), and the
tombstone field (task 4) exists before anything writes a SHA into it.

Task 5's step 1 has a real choice inside it — writing the graveyard entry and the
SHA of the commit that contains it is circular, since the SHA is not known until
the commit exists. Amending is the obvious resolution and is safe here because
the commit has not been published yet at that point, but the implementation
should state which it chose and why in a comment, because the next reader will
wonder.
