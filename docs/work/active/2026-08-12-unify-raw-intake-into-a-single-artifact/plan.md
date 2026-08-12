# Plan — Unify raw intake into a single artifact

Ordered so the suite is green at every commit boundary. The ordering principle
here is **the presence rule before the fallback**: every task after task 2 is
safe only because one resolver already governs what "present" means.

## Tasks

### 1. Register `intake` as an artifact

**Changes:** `tcw/store/base.py:780` — append `"intake"` to `WORK_ARTIFACTS`.

**Verified by:** the existing suite, unmodified. Nothing yet writes an
`intake.md`, so `artifacts()` gains one always-absent entry, `read_artifact` /
`write_artifact` accept the new name, and no behavior changes.

**Why alone and first:** it is the one change that is inert. Anything that fails
here fails because something depends on `WORK_ARTIFACTS`' exact contents, and
finding that out on its own commit is worth the extra boundary.

### 2. One presence rule

**Changes:** `tcw/store/fs.py` — add `_resolve_body(d) -> (name | None, text)`
implementing *exists and non-empty after `.strip()`*, resolving
`initial-request.md` → `intake.md` → `(None, "")`. Route `_read_item`
(`fs.py:2387`), `artifacts()` (`fs.py:2166-2177`), and `body_path`
(`fs.py:2158-2160`) through it. `body_path` now returns `None` when neither file
is present.

**Verified by:** new tests for all four states — request only, intake only, both,
neither — asserting body text, `artifacts()` presence, and `body_path`. Plus the
existing suite: every item it creates still has a request, so every existing
assertion must hold unchanged. **If any existing test changes here, the resolver
is wrong** — the fallback is not reachable yet.

Grep `body_path` at this point and confirm every caller handles `None`.

### 3. Hash what the body resolved to

**Changes:** `fs.py:2904-2907` — `get_detail`'s core revision becomes
`_revision_multi(state_text, name or "", body_text)` from `_resolve_body`.

**Verified by:** a test that an item's revision differs from an otherwise
identical item whose same text sits in the other file. Deferred to its own task
rather than folded into task 2 because it is the one change that alters an
observable token for **every existing item**, and it should be attributable.

### 4. The intake creation argument

**Changes:** `base.py:944` — add `intake: str = ""` to the abstract `create`, and
to `create_work` (`base.py:1060`, `fs.py:2931`). In `create_work`
(`fs.py:3015-3035`): write `initial-request.md` only when `body` is non-empty,
write `intake.md` when `intake` is non-empty, write neither when both are empty.
The three-heading template is deleted. `_stage` receives only the files actually
written.

**Verified by:** store-level tests for each of the four combinations, asserting
the exact folder contents rather than two path checks (criteria 1 and 2). The
rollback path is exercised by an existing test if one covers it; if not, this
task does not add one — the `except BaseException: rmtree` block is unchanged.

**This is the task that breaks tests.** Any test asserting `## Product changes`
after a create is asserting the removed template. Each such edit is deliberate
and gets named in `outcome.md`.

### 5. `tcw work new` passes intake

**Changes:** `tcw/work/cli.py:224` — `body=_stdin_body()` → `intake=_stdin_body()`.
`_stdin_body` itself is unchanged. The `→ edit:` hint (`work/cli.py:240-242`)
needs no change: its `if body is not None` guard already covers `body_path`
returning `None`.

**Verified by:** a CLI-level test with and without piped stdin, asserting folder
contents (criteria 1 and 2).

### 6. `inbox_accept` writes intake

**Changes:** `fs.py:2756-2761` — replace the request template with intake
assembly. The manifest (`fs.py:2751-2755`) keeps its `— accepted from` suffix,
with `initial-request.md` → `intake.md` in both the manifest entry
(`fs.py:2745`) and the suffix test (`fs.py:2753`). The binary fallback string
(`fs.py:2755`) is kept verbatim. `### Inbox manifest` / `### Inbox body` become
`##` now that `## Inbox contents` is gone. Attachments, temp-dir assembly, and
`os.replace` are untouched.

**Verified by:** the three entry shapes of criterion 3 — a text file, a folder
with an `INDEX.md` plus resources, and a binary-only entry — each asserting
`intake.md` present, `initial-request.md` absent, attachments copied, manifest
correct, and (third case) the fallback prose present.

### 7. The write contract and promotion

**Changes:** `update_work` (`fs.py:3057`) keeps targeting
`initial-request.md`; add a `promoted` flag to what it reports when it created
that file on an item that had only intake. `tcw work edit` prints
`→ promoted: created initial-request.md (intake preserved)` on stderr;
`serve`'s PATCH response (`serve/__init__.py:996-1000`) gains `"promoted": true`,
additively.

**Verified by:** criterion 8 — the promotion writes the request, leaves
`intake.md` **byte-identical** (compared as bytes, not text), and reports itself,
through both `tcw work edit` and `serve`'s PATCH path. Plus criterion 9: identical
text still changes the revision, which task 3 already made true and this task
proves end to end.

The `serve` test is not optional. The web editor shares this code path, and a
store-level test alone would not have caught it.

### 8. The board letter

**Changes:** `tcw/work/cli.py:314-322` — add `"intake": "i"` and sort the
rendered letters through a display-order tuple with `intake` first. The
`labels.get(..., "?")` fallback stays.

**Verified by:** criterion 5 — one test asserting all four board states (fresh,
intake-only, `iR`, legacy `R`).

Last among the code tasks because it is the only purely cosmetic one, and by here
every state it renders can actually be produced.

### 9. Capability ledger

**Changes:** `tcw capabilities add work/capture-raw-intake "Capture raw intake"
--status Missing`, then `set --field "Planning doc=<this slug>"`,
`--field "Feature=work-inbox"`, `--field "Subject=work-item"`, and a
`description.md`. Record `changed:` for `work/open-a-work-item` and
`work/manage-the-work-inbox` in this item's `capabilities.yaml`.

Rewrite both changed entries' prose: `work/open-a-work-item`'s
"`initial-request.md` is always-present…" sentence and
`work/manage-the-work-inbox`'s "generates the durable `initial-request.md`".

**Verified by:** `tcw capabilities check` and `tcw capabilities drift` clean. The
`Missing` → `Supported` flip is the completion gate's, not this task's.

## Documentation Sync

Evaluated against `CLAUDE.md`. One block, after the code tasks, answered in a
single pass over the finished diff.

### 10. `docs/changelogs/upcoming.md` [Any-Code-Change] — **fires**

Grouped entries: Added (`intake.md` artifact, the `intake` creation argument, the
`i` board letter), Changed (creation writes no request template; `inbox accept`
writes intake; one presence rule; core revision hashes the resolved artifact
name), Removed (both hardcoded request templates).

### 11. `docs/release-notes/upcoming.md` [Public-API] — **fires**

**Lead with `tcw work new` no longer leaving a file to edit.** That is the change
an existing user will hit first and the one most likely to read as a bug. Plain
language: what lands where now, what `i` means on the board, and that editing an
intake-only item's body creates its request.

### 12. `README.md` [Public-API] — **fires**

The `tcw work new` description, the `inbox accept` description, and the board's
stage-letter legend wherever it is documented. Grep `README.md` for
`initial-request` before writing — the file is the place the old model is most
likely to be restated in passing.

### 13. `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — **fires**

- `references/stage-request.md:18-19` — the sentence claiming
  `initial-request.md` "is the always-present body and overview surface, so it is
  never absent" is now false. C1 fixes this sentence; the router rewrite is C7's.
- `SKILL.md`'s stage/artifact table and "Finding your place" — `intake.md` is an
  artifact with no stage, and the `inbox` row is a stage with no artifact. Say so
  once; do not restructure the table, which C7 owns.
- Grep the whole `skills/tcw-work/` tree for `initial-request` and fix every
  claim the new model falsifies. A scope inherited from the two files above is a
  scope nobody chose.

## Verification

What the suite cannot check:

- **That `tcw work new` still feels right.** No test covers a user's expectation
  of a file to open. Run it by hand, with and without piped input, and read the
  stderr hints as a user would, before `submit`.
- **That the release note is honest about the surprise.** Judgment, not a check.
- **That `serve`'s web editor promotes correctly in the browser.** Criterion 8
  tests the PATCH handler; nobody tests the UI. Worth clicking once through
  `tcw serve` on an intake-only item.
- **That no doc restates the old model somewhere unsearched.** The greps in tasks
  12 and 13 cover `README.md` and `skills/tcw-work/`; a claim living in a
  capability body or a release note for an old version would survive them.

## Notes

- Tasks 1–3 are preparation that changes no behavior; 4–8 change behavior one
  surface at a time; 9–13 are the ledger and the docs. The suite should be green
  after every one of them, and the only task expected to *edit* existing tests is
  task 4.
- No blockers to record beyond the one already set: this item is blocked by
  nothing, and C2 is already `--blocked-by` it.
