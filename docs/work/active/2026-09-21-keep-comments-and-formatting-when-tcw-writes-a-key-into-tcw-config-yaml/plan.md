# Plan: keep comments and formatting when tcw writes a key into tcw-config.yaml

Implements `spec.md` in this folder. Work happens in `.worktrees/<slug>/` on
`work/<slug>`. Every test run is bare `pytest` from the worktree root, as CI runs it,
with the editable install re-pointed at the worktree (or a venv) per `CLAUDE.md`.
Because this change edits `tcw/`, the lifecycle is driven by hand-editing
`docs/work/` rather than through the `tcw` CLI once implementation starts.

## Shape of the change

- **New module `tcw/store/config_edit.py`** holds the whole text-editing routine:
  reading and writing the bytes, locating keys with `yaml.compose()`, the edits, the
  two-part verification and the refusal messages. It is private to the filesystem
  adapter (only `tcw/store/fs.py` imports it) and has no knowledge of stores. Putting it
  in its own file keeps the `fs.py` diff down to the five writer functions, which
  matters because two parallel items also edit `fs.py` (the leftover-config item, and
  the child-status item, which edits it heavily).
- **`tcw/store/fs.py`** changes only in: `write_sentinel` (157-176), `init`'s pre-flight
  and config write (955-1084), `_atomic_write_all` (one argument on one line, 1500),
  `_persist_extends` (1768-1807), `_write_node_config` (1818-1845), `_write_tags`
  (5772-5801). `dump_yaml` stays; the `state.yaml` writers still use it
  (`fs.py:3959`, `4052`, `6112`).
- **The abstract interface does not change.** `tcw/store/base.py` is untouched:
  `extends_add`, `extends_remove`, `register_tags`, `unregister_tags` keep their
  signatures. Keeping a text file's layout is a filesystem-adapter detail with no
  analog in another store, which is why it lives behind `fs.py`.

### Interface of `config_edit.py` (what later tasks rely on)

```python
class ConfigEditRefused(ValueError): ...      # message is the full user-facing refusal

@dataclass(frozen=True)
class SetList:   section: str; key: str; values: tuple[str, ...]
@dataclass(frozen=True)
class SetScalar: section: str; key: str; value: str
@dataclass(frozen=True)
class Remove:    section: str; key: str       # also drops the section if left empty
@dataclass(frozen=True)
class SetId:     value: str                   # top-level `id`

def read_text(path: Path) -> str | None       # None when absent; newline="" and utf-8
def intended(mapping: dict, edits) -> dict    # the mapping with the edits applied
def edit_text(path: Path, text: str | None, edits) -> str | None
    # None → nothing to write (the edits change nothing).
    # Missing, empty or whitespace-only text → yaml.safe_dump(intended(...)) as today.
    # Otherwise the spliced text, verified; ConfigEditRefused on any failure.
```

`path` is passed only so refusal messages can name the file. A refusal message
always starts `<path>: cannot <add|change|remove> <section>.<key> without rewriting
the file, which would lose its comments and formatting; ` followed by the
instruction chosen per spec, "Refusal messages".

## Tasks

Each task ends with the full suite green and is one commit.

### Task 1 — the edit routine for scalars, `id`, new keys, new sections and removal

**Creates** `tcw/store/config_edit.py`, `tests/test_config_edit.py`.

Build, in `config_edit.py`:

1. `read_text` — `open(path, encoding="utf-8", newline="")`; no line-ending translation;
   a leading byte-order mark stays as the character `﻿` in the returned text.
2. Line-ending detection (`\r\n` if the first line break is `\r\n`, else `\n`) and the
   indent unit rule from the spec (section's key column minus section column; else from
   the first top-level block mapping; else 2).
3. Locating: `yaml.compose(text)`; refuse if the root is not a block mapping (a flow
   top level) — except when the text is missing/empty, handled before composing. Find
   the section key and value nodes, then the key inside a block-mapping section.
4. The span each edit replaces, per the spec's "What each edit does":
   - `SetScalar` on a single-line scalar: the scalar's own start..end marks. Refuse a
     block scalar (`style in "|>"`) or a scalar whose start and end lines differ.
   - Null written as nothing (zero-width null: start mark == end mark): a zero-width span
     at the **end of the key's line** (before its line break), inserting
     `<nl><indent>key: …` or, for a null section, the new key lines. Explicit `null`/`~`:
     the token's span.
   - Key absent in a block section: zero-width span at the end of the line holding the
     section's last entry's last character. The end of a block collection is found as
     the end of the line holding the last character of its last scalar descendant
     (block collection end marks overrun trailing comments); for a block scalar or
     multi-line last entry, the end mark if it is at column 0, else end of its line.
   - Section absent, and `SetId` in a file with no keys: zero-width span at end of
     document — before a final line that is exactly `...` if present — with a leading
     line break added when the text does not end with one.
   - `SetId` otherwise: an existing `id` with a null value is replaced as a null;
     else a zero-width span at the start of the line of the first top-level key.
   - `Remove`: from the start of the key's line to the end of its last value line
     (including the line break). If the section has no other entries, the span grows to
     start at the section key's line. Comment lines above the key are outside the span.
   - Flow-mapping section (`{…}`): only replacing an existing key's value is allowed;
     adding or removing a key there is refused with the "inside the braces" message.
   - Target value is an alias: detected as a value node whose start mark lies before its
     own key node's end mark (the alias shares the anchored node, so its marks point at
     the anchor). Refused.
   - Section present but not a mapping and not null: refused (the per-writer rules in
     the spec's table are applied by the callers in Tasks 3-4, which decide whether to
     raise their existing message first; this function refuses in any case).
5. Rendering: scalars plain when `yaml.safe_load(plain) == value`, otherwise
   double-quoted via `json.dumps` (valid YAML); lists in block style at the given dash
   column; new lines joined with the file's line ending.
6. **Verification** (`_verify(original, new, spans, allowed_comments, intended)`):
   - Same meaning: parse `new` with the same unique-key loader `load_config` uses and
     compare with `intended`. `config_edit.py` imports `_UniqueKeyLoader` from `fs.py`
     lazily inside the function to avoid a circular import, or the loader class moves
     to `config_edit.py` and `fs.py` imports it — pick the latter only if the import
     cycle appears; either way `load_config` behavior is unchanged.
   - Confined: walk the spans in order and check that every stretch of `original`
     between spans appears unchanged at the matching place in `new` (prefix, gaps,
     suffix), independently of how `new` was assembled.
   - No anchor inside any span: `yaml.scan(original)` `AnchorToken` positions.
   - No unentitled comment inside any span: a comment is a `#` at line start or after
     whitespace whose position lies in no scanned token's start..end range. Comments at
     positions listed in `allowed_comments` (a removed item's end-of-line comment) pass.
   - Any failure → `ConfigEditRefused` with the instruction message.
7. No-op: when `intended(mapping, edits) == mapping`, return `None` before editing.
8. Refusal instructions, exactly as the spec's "Refusal messages" lists them. The value
   is always rendered in flow style on one line (`extends: [a, b]`).

**Tests** (`tests/test_config_edit.py`, pure text in, text out, no git), table-driven:

- Scalar replaced keeps an end-of-line comment (AC 10, text level).
- New key in a 4-space block section; new key in a section whose last entry is followed
  by a comment line (comment stays below the section) (AC 1, 7).
- Section appended at end; before a trailing `...`; to a file without a final line break
  (AC 2, 9).
- `SetId` below a leading comment block, after `---`; `id: null` replaced (AC 13).
- `Remove`: key lines only; section line too when empty; comment above key stays (AC 3).
- Stub section `taxonomy:` with commented children, and `extends: # note`, keep every
  comment (AC 8).
- `\r\n` text keeps `\r\n` everywhere, including inserted lines; leading `﻿` kept
  (AC 9, text level — raw bytes are checked in Task 3).
- Refusals: flow section needing a key added (message contains "inside the braces" and
  `, extends: [x]`) (AC 14); target alias; anchor inside a removal span (AC 15); block
  scalar target (AC 16); flow top level; non-mapping section.
- Messages: removal message holds no `taxonomy:` block; add-to-existing-section message
  says not to add a second section (AC 20).
- Empty and whitespace-only text → full `safe_dump` output; comment-only text → edited
  (AC 12, text level).
- Mutation check for the verifier (per `CLAUDE.md`'s rule for instruments): a test that
  feeds `_verify` a `new` text with one comment deleted outside the spans, and one with a
  change inside an anchor, and asserts each is refused — then, while writing it, confirm
  the test goes red with the corresponding check commented out.

### Task 2 — list edits: incremental, whole-list replacement, no-op

**Modifies** `tcw/store/config_edit.py`, `tests/test_config_edit.py`.

1. `SetList` on an existing list: *incremental* when both `old` and `new` are free of
   duplicates and `[x for x in old if x in new] == [x for x in new if x in old]`.
   - Block list: each removed item's span is its whole line (start of line through the
     line break), and its end-of-line comment position goes into `allowed_comments`;
     each added item is a zero-width insertion after the line of the item preceding it in
     `new`, or at the start of the first surviving item's line, at the existing dash
     column. Refuse if any item's start and end lines differ.
   - Flow list on one line: insert `, x` after the preceding item (or `x, ` before the
     first surviving item); remove the item and one adjoining `, `. A multi-line flow
     list containing a comment is refused; one without comments may be replaced whole.
   - Emptying via a list edit (`tags rm` of the last tag) writes `tags: []` — replace
     the whole value with `[]`, matching today's `fs.py:5793-5800`.
2. Not incremental: replace the whole value in its existing style and dash column only
   if no comment lies within the list's lines; otherwise refuse (message gives the full
   new list in flow style).
3. `SetList` with the key absent or null: the rules from Task 1.

**Tests:**

- Block `extends` of `a # ca`, `# between`, `b # cb`: add `c` inserts one line after
  `b`; rm `a` deletes only `a`'s line; `# between` and `# cb` survive (AC 3).
- Sorted flow `tags: [a, c]` + `b` → `tags: [a, b, c]` on the same line; sorted block
  list with per-item comments + one tag inserts one line; rm removes one line (AC 4).
- Comment line right after the list, before the next key, survives add and rm (AC 7).
- Adding an already-present item returns `None` (AC 5, text level).
- Unsorted block list without comments → whole replacement, nothing outside changed;
  with a comment → refused (AC 6).
- Dash column preserved for both `- a` under the key and `    - a` indented.

### Task 3 — wire the store writers: `extends` and `tags`

**Modifies** `tcw/store/fs.py` (`_atomic_write_all`, `_persist_extends`,
`_write_node_config`, `_write_tags`, and the two docstrings named in the spec);
**creates** `tests/test_config_edit_writers.py`.

1. `_atomic_write_all`: `tmp.write_text(content, encoding="utf-8", newline="")`
   (`fs.py:1500`). No effect on Linux or macOS today, where text mode does not translate
   on write; it makes the config's computed bytes exact on every platform.
2. `_write_node_config(self, edits)`: read with `config_edit.read_text`, parse with
   `load_config` semantics for the mapping, call `edit_text`; if it returns `None`,
   return without writing or staging; else write through the existing
   `_atomic_write_all` / `_write_staged(stage_root=node_repository)` branch unchanged.
   Replace the docstring's "`yaml.safe_dump` re-renders the file…" paragraph with the
   new contract.
3. `_persist_extends(extends)`: keep the existing non-mapping-section refusal
   (`fs.py:1787-1793`); build `SetList(COMPONENT, "extends", tuple(extends))` or
   `Remove(COMPONENT, "extends")`; call `_write_node_config([edit])`; only then update
   `self.config` (move `fs.py:1778-1781` after the write).
4. `_write_tags(tags)`: if `work` is present, not null and not a mapping, raise
   `ValueError(f"{config_path}: work must be a mapping, found {type}")` (replaces the
   silent normalization at `fs.py:5794-5796`); if `work.tags` is present and not a list,
   refuse the same way. Build `SetList("work", "tags", tuple(sorted(tags)))`. Return value
   unchanged. Replace the docstring sentence about `dump_yaml` dropping comments.

**Tests** (`tests/test_config_edit_writers.py`; fixtures follow
`tests/test_capabilities_federation.py`'s `repo`/`child_of` for registered projects and
`tests/test_work_tags.py`'s `node`; commands run through `tcw.cli.main`; every comparison
reads raw bytes with `read_bytes()`; every refusal also asserts
`git diff --cached --quiet` succeeds and the bytes are unchanged):

- AC 1: the annotated 4-space file from the spec, `tcw taxonomy extends add base`.
- AC 2: `tcw capabilities extends base` with no `capabilities:` section; and with a
  trailing `...`.
- AC 3: `tcw taxonomy extends rm` of one of two ids, then of the last.
- AC 4, 5: `tcw work tags add|rm` on flow, block and absent `tags`; re-adding an
  existing tag leaves bytes identical and nothing staged.
- AC 6: unsorted `tags` without and with a comment.
- AC 8: stub `taxonomy:` with commented children; `extends: # note`.
- AC 9: a `\r\n` file and a byte-order-mark file through `tags add`, checked on bytes.
- AC 14: `taxonomy: {path: docs/taxonomy}` + `extends add` → exit 1, message checked.
- AC 15: `tags: *x` + `tags add` refused; `extends: &ids [a, b]` aliased elsewhere +
  `extends rm a` refused.
- AC 17 (tags half): `work: docs/work` + `tags add` → exit 1, message names `work` and
  the file.
- AC 18: open one `FsTaxonomyStore`, provoke a refused `extends_add`, assert
  `st.config.get("extends")` is unchanged, fix the file, `extends_add` again, and assert
  the file gained only that id.

Existing tests to re-run with attention: `tests/test_work_tags.py`,
`tests/test_taxonomy.py` (the `taxonomy: docs/taxonomy` refusal at ~1010 must still
produce its existing message, which `_persist_extends` raises before the edit routine),
`tests/test_capabilities_federation.py`, `tests/test_non_git_writes.py`,
`tests/test_external_work_store.py` (tags staged in the node repository).

### Task 4 — wire `init` and `write_sentinel`, one write before any folder change

**Modifies** `tcw/store/fs.py` (`write_sentinel`, `init`); **extends**
`tests/test_config_edit_writers.py`.

1. A module-level helper in `fs.py`, `_sentinel_edits(existing, project_id)` →
   `[SetId(project_id)]` when `existing.get("id")` is absent or null (after today's
   conflicting-id and non-string checks, `fs.py:161-170`), else `[]`.
2. `write_sentinel(root, project_id=None) -> bool`: same signature and return meaning;
   builds `_sentinel_edits`, calls `edit_text`, writes with `_atomic_write_all` (not
   staged) when there is text. Returns `True` only when it wrote. The intended mapping
   sets `id` to the project id, fixing the `id: null` defect.
3. `init`: in the pre-flight, after the existing checks and before line 1063's
   gitignore probe loop ends the pre-flight, compute one edit list — `_sentinel_edits`
   plus `SetScalar(component, "path", str(location))` for each configured component —
   refusing first, with `ValueError(f"{root / SENTINEL}: {component} must be a mapping,
   found …")`, when a configured component's section is present, not null and not a
   mapping (replaces the silent normalization at `fs.py:1080-1083`). Call `edit_text` there,
   so a refusal happens before anything is written. In the write phase, replace
   `write_sentinel(root, project_id)` (`fs.py:1073`) with one `_atomic_write_all` of the
   verified text (skipped when `None`), and delete the second read-modify-write
   (`fs.py:1078-1084`). The `shutil.rmtree` (`fs.py:1076-1077`) and folder creation
   stay where they are, now after the only config write.
4. Default id fallback (`project_id or "test-project"`, `fs.py:173`) stays inside
   `write_sentinel`; `init` passes the id it already validated.

**Tests:**

- AC 10: `init(["work"], root, work_path=...)` on a commented config without `id`
  changes only the `id` line and the `work.path` line; a commented `taxonomy.path`
  replaced by `init(["taxonomy"], root, paths={"taxonomy": ...})` keeps its end-of-line
  comment.
- AC 11: a node initialised with a pristine default `docs/work/`, then its config set to
  `work: {tags: [a]}` (flow), then `tcw init --work-path <dir>` → exit 1; config bytes
  unchanged, `git diff --cached --quiet`, `docs/work/` still present, `<dir>` not created,
  no `id` line added (the fixture's config starts without `id` and is passed `--id`).
- AC 12: `tcw init --id x` with no config file, and with an empty one, succeeds and
  the file parses to the expected mapping.
- AC 13: `write_sentinel` on a commented file without `id`, and on `id: null`; the
  existing `tests/test_store_nodes.py:67-68` (`True` then `False`) still passes.
- AC 16: `taxonomy.path: |` block scalar + `init(["taxonomy"], paths=...)` refused.
- AC 17 (init half): `work: docs/work` + `tcw init --work-path` refused with the message.

### Task 5 — equivalence with today's writer

**Extends** `tests/test_config_edit.py`.

A table of input shapes (block and flow lists, absent section, null section, absent key,
4- and 2-space indent, `\r\n`, comment-heavy) × each edit kind. For each, compute the
old result the way today's code does — a small reference function in the test that
reproduces `_persist_extends` / `_write_tags` / `init` / `write_sentinel`'s dict logic
and `yaml.safe_load(yaml.safe_dump(...))` — and assert `yaml.safe_load(new_text)` equals
it, except `id: null` (AC 19).

### Task 6 — Documentation Sync, one pass over the finished diff

Run the `documentation-sync` skill and act on each entry:

| Entry | Fires? | Action |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` — Any-Code-Change | yes | Under **Fixed**: config writers edit only the changed key's lines (all five writers named), `write_sentinel` `id: null`, `\r\n` preserved. Under **Changed**: the three newly refused shapes (`work: <scalar>` on `tags add|rm`, a non-mapping section on `init --path`, `work.tags` holding a non-list), and refusal of flow sections, aliases, block scalars and commented unsorted tag lists. Under **Internal**: `tcw/store/config_edit.py`, `_write_node_config` takes key edits. |
| `docs/release-notes/upcoming.md` — Public-API | yes | Plain-language paragraph: `extends` and `tags` commands and `tcw init` now keep comments and layout; when a file cannot be edited safely the command says what to add by hand; list the newly refused shapes in plain words. |
| `docs/guide/<topic>.md` — Guide-Topic-Change | yes (what a command writes to disk) | `docs/guide/taxonomy-and-capabilities.md:50-52`: add that `extends add` changes only the `taxonomy.extends` lines and refuses a file it cannot edit safely. `docs/guide/work.md:322-324`: the same for `tcw work tags add|rm`. |
| `skills/configure/references/<document>.md` — Configuration-Key-Change | no key changes meaning, but the document states the old behavior | `skills/configure/references/projects.md:104-107`: replace the "re-renders" sentence with the new behavior. |
| `README.md` — Public-API | evaluate | README lists the commands (311, 362, 371) without describing how they write; expected no change. Confirm by reading. |
| `skills/<component>/SKILL.md` — Skill-Driven-Component | evaluate | `skills/work/SKILL.md`, `skills/taxonomy/SKILL.md`, `skills/capabilities/SKILL.md` do not describe how the config is written (checked with `grep -n "tags add\|extends\|rewrit\|comment"` at plan time); expected no change. Confirm on the final diff. |
| `docs/guide/jira.md` — Tracker-Change | no | Nothing about the tracker changes. |

Also, outside the documentation entries but named by the spec:

- `docs/migration-guide-2.4.X-to-2.5.0.md:105-110`: replace the section "One more thing:
  writing the key re-renders the file" with one saying the commands change only their
  own lines and refuse a file they cannot edit safely. Touch only that section — the
  leftover-config item edits other parts of this file in parallel.
- Capability ledger (planned deltas from the spec): edit
  `docs/capabilities/capabilities/federate/description.md`,
  `docs/capabilities/taxonomy/federate-shared-vocabulary/description.md` and
  `docs/capabilities/work/tag-a-work-item/description.md` by hand (the CLI is not driven
  while `tcw/` is being changed), adding the one sentence each from the spec's
  "Capability changes". No status change.

**Proves it:** AC 22 — `grep -rn "re-render" docs/migration-guide-2.4.X-to-2.5.0.md
skills/` returns nothing; `grep -n "comments and formatting do not\|dropping its stub
comments" tcw/store/fs.py` returns nothing.

## Verification

What the suite cannot check, done by hand at `verify`:

1. **The original report, reproduced.** In a scratch copy of a realistic annotated
   config (4-space indent, comments in `work.lifecycle` and documentation descriptions,
   a long `work.tracker.candidate-query`), run `tcw taxonomy extends add <id>` and
   `tcw capabilities extends <id>` against a registered project; `git diff` shows only the
   added `extends` lines (the report's expected 9+ shape, not 31+/22-).
2. **Refusal messages read correctly to a person.** Trigger each refusal kind once
   (flow section, removal refused, alias, `work: docs/work`) and read the message: does
   following it literally produce a valid file without a duplicate section or a lost
   sibling key? Paste the instruction and run the command again to confirm.
3. **AC 21:** `git diff main -- pyproject.toml` shows no dependency change.
4. **AC 23:** bare `pytest` from the worktree root passes in full.
5. Windows behavior (`newline=""` on write) cannot be exercised on the Linux CI or on
   macOS; it is covered only by reading the code.

## Notes

- **Acceptance criteria coverage.** AC 1 T1/T3; AC 2 T1/T3; AC 3 T1/T2/T3; AC 4 T2/T3;
  AC 5 T2/T3; AC 6 T2/T3; AC 7 T1/T2; AC 8 T1/T3; AC 9 T1/T3; AC 10 T1/T4; AC 11 T4;
  AC 12 T1/T4; AC 13 T1/T4; AC 14 T1/T3; AC 15 T1/T3; AC 16 T1/T4; AC 17 T3/T4; AC 18 T3;
  AC 19 T5; AC 20 T1; AC 21 Verification 3; AC 22 T6; AC 23 Verification 4.
- **No blockers recorded.** The leftover-config item and the child-status item touch
  the same files but not the same functions or migration-guide section; there is no
  dependency in either direction, so no `--blocked-by`. Whichever lands second rebases;
  the combined diff of `fs.py` and the migration guide should be reviewed once both have
  landed, per the user's rule on changes that share a file.
- **Riskiest code** is the span computation and the verifier (Tasks 1-2). They land
  first, as pure text functions with their own tests and a mutation check, before any
  command uses them; Tasks 3-4 only wire them in.
- The `_UniqueKeyLoader` import direction (Task 1, step 6) is the one decision left to
  implementation, because it depends on whether an import cycle actually appears; both
  choices leave behavior identical.
