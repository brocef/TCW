# Spec: keep comments and formatting when tcw writes a key into tcw-config.yaml

## Capability changes

Planned amendments to the standing ledger (wording only; no status changes, no new
capabilities). Nothing is written to the ledger at this stage.

- **`capabilities/federate`** (cap-7b8d42) and **`taxonomy/federate-shared-vocabulary`**
  (cap-24da21): add that `extends` writes change only the `extends` lines of
  `tcw-config.yaml`, and that a file TCW cannot edit that way is refused with
  instructions for making the change by hand, rather than rewritten.
- **`work/tag-a-work-item`** (cap-609d75): the same sentence for the registered tag
  set that `tcw work tags add` / `rm` maintain in `tcw-config.yaml`.

No taxonomy change: the operations already exist under the `node` Vocabulary entry
and the `connected-project-registry` Feature; only how the file is written changes.

## Problem

Every `tcw` command that writes a key into a node's `tcw-config.yaml` rewrites the
whole file with `yaml.safe_dump`. That keeps keys, values and key order, but deletes
every comment, reflows long strings across lines, re-quotes values and switches the
indentation to PyYAML's own (2 spaces, with list dashes not indented under their
key). The file is the one TCW file people annotate by hand, so this destroys their
work silently; the 2.5.0 migration guide sends everyone who federates through two of
these commands.

The writers, found by a repository-wide sweep of `tcw/` for writes of the sentinel
file (`SENTINEL = "tcw-config.yaml"`, `tcw/store/fs.py:156`) — every one goes through
`yaml.safe_dump`:

1. **`FsTreeStore._write_node_config`** (`tcw/store/fs.py:1818-1845`) serialises the
   whole mapping at `fs.py:1840`, then writes it atomically and stages it in the
   node's repository (`fs.py:1841-1845`). Its docstring accepts the loss
   (`fs.py:1834-1836`). Callers:
   - `_persist_extends` (`fs.py:1768-1807`), reached from `extends_add` /
     `extends_remove` on the taxonomy store (`fs.py:2249`, `fs.py:2257`) and the
     capabilities store (`fs.py:2962`, `fs.py:2970`) — the commands
     `tcw taxonomy extends add|rm` (`tcw/taxonomy/cli.py:148-168`) and
     `tcw capabilities extends [--rm]` (`tcw/capabilities/cli.py:161-164`).
     It updates the in-memory `self.config` (`fs.py:1778-1781`) *before* writing, so
     a failed write leaves the store object believing a change that never landed.
   - `FsWorkStore._write_tags` (`fs.py:5772-5801`), reached from `register_tags` /
     `unregister_tags` (`fs.py:5803-5809`) — `tcw work tags add|rm`
     (`tcw/work/cli.py:3421-3456`). Its docstring also accepts the loss
     (`fs.py:5773-5775`). A `work` section that is not a mapping (`work: docs/work`)
     is silently replaced (`fs.py:5794-5796`).
2. **`init`**, when a component location is configured (`tcw init --work-path`,
   `tcw <component> init --path`): it sets `<component>.path`, silently replacing a
   section that is not a mapping, and writes the whole file with `dump_yaml`
   (`fs.py:1078-1084`; `dump_yaml` is `fs.py:1229-1230`, a plain `write_text`: not
   atomic, not staged).
3. **`write_sentinel`** (`fs.py:157-176`), called by `init` (`fs.py:1073`): when the
   file has no `id` it builds `{"id": <id>, **existing}` and writes the whole file
   with `dump_yaml` (`fs.py:174-175`). This is the path `tcw init --id` takes on a
   legacy node that predates project ids.

**`init` writes the file twice around a deletion.** `write_sentinel` writes `id`
(`fs.py:1073`), then `shutil.rmtree` may delete the default work store when it is being
replaced (`fs.py:1076-1077`), then the path is written (`fs.py:1084`). Once edits can be
refused, a refusal at the second write would leave `id` written and the default store
already deleted.

No other code writes the file: `tcw serve`, provisioning and the tracker code only
read it (`grep` of `tcw/` for `write_text`, `dump_yaml`, `safe_dump`,
`_atomic_write_all` and `_write_staged`).

**Line endings are lost on read, independently of `safe_dump`.** Every reader uses
`Path.read_text` (`fs.py:1198` in `load_yaml`), which in Python's default text mode
turns `\r\n` into `\n`. Any surgical edit built on that text would still convert a
Windows-line-ending file.

**A sibling defect found in the same sweep.** `write_sentinel` reads `id: null` as
"no id" (`fs.py:161-162`), then builds `{"id": project_id, **existing}` — and because
`existing` is spread *after* the new id, its `None` wins. Reproduced against the tree:
a file holding `id: null` comes back still holding `id: null`, the function returns
`True` ("backfilled"), and the comment in the file is gone. This change rewrites that
function's write anyway, so it fixes this too.

## Goals

1. When one of the writers above changes a key in an **existing, non-empty** file, only
   the lines belonging to that change differ. Every other byte — comments, blank lines,
   key order, quoting, line wrapping, indentation, line endings, a leading byte-order
   mark — is identical before and after.
2. A change that does not change the parsed mapping (adding a tag that is already
   registered, for example) does not write the file at all.
3. No new runtime dependency. `pyproject.toml` keeps `PyYAML` as the only one.
4. Every edit is verified before it is written (see Design, "Verification"). An edit
   that cannot be made and verified is **refused**: nothing is written — no config, no
   folders created or deleted, nothing staged — and the message says exactly what to
   change by hand. TCW never falls back to rewriting a non-empty file.
5. A missing file, or one that is empty or holds only whitespace, is written in full as
   today; a fresh `tcw init` never refuses on account of this change. A file holding
   only comments counts as content and is edited, not rewritten.
6. The two documents and two docstrings that currently promise the loss (listed under
   Design, "Documentation to change") stop doing so.

## Non-goals

- **Other YAML files TCW writes.** `state.yaml`, taxonomy and capability `meta.yaml`,
  tombstone records (`fs.py:4829`) and tracker intake files are TCW's own records,
  written whole by design. People can hand-edit them, but nobody is told to annotate
  them. Out of scope; a separate item if it ever matters.
- **A general YAML editor.** This supports exactly the edits the writers make: set a
  list-of-strings value, remove a key, set a string value, set `id`. Nothing else.
- **A flag to force the old whole-file rewrite.** Not added unless someone asks.
- Changing *what* is written, beyond the refusals listed under "Sections and keys
  that are not what the writer expects": `extends` removal still drops an emptied key
  and then an emptied section (`fs.py:1800-1806`); `tags rm` still writes the remaining
  sorted list, including `tags: []` (`fs.py:5793-5800`); staging in the node's
  repository stays for the store writers, and `init` still stages nothing.

## Design

### Where it lives (abstraction litmus test)

"Set a key in the node's configuration" is an abstract operation any store could
implement, and it stays expressed that way: `extends_add`, `extends_remove`,
`register_tags` and `unregister_tags` in `tcw/store/base.py` do not change. *Keeping a
text file's comments and layout* has no meaning outside a text file, so it is a private
detail of the filesystem adapter in `tcw/store/fs.py` (or a private module beside it),
used only by the three writers in the Problem. The behavior lives in the `tcw` CLI, so
it is identical under Claude and Codex; no skill or hook carries any of it.

### The edit is described as key paths, not as a whole mapping

`_write_node_config` stops taking the whole mapping. Its callers pass a list of **key
edits**, each one of: set `<section>.<key>` to a value, remove `<section>.<key>`, or set
the top-level `id`. The same edit routine serves `init` and `write_sentinel`, so all
three writers share one implementation and one verification. The *intended mapping* is
the parsed original with those edits applied (removing a key that empties its section
also removes the section, as today). Nothing else in the mapping may differ.

### Reading and writing the bytes

The file is read with line endings untranslated (`newline=""`, UTF-8) and written the
same way, so the bytes written are exactly the text computed. A leading byte-order mark
is carried through unchanged. Inserted lines use the file's own line ending: `\r\n` if
the file's first line break is `\r\n`, otherwise `\n`.

- `_write_node_config` keeps today's write path: atomic write (`_atomic_write_all`,
  `fs.py:1470`), staged in the node's repository (`fs.py:1841-1845`).
- `init` and `write_sentinel` switch from `dump_yaml`'s plain write to the atomic write,
  still unstaged, as everything `init` writes is today.

### How the text is located

`yaml.compose()` returns the parsed tree with a start and end position (a *mark*:
character offset, line and column) for every key and value. The edit uses those
positions to find the top-level section and the key inside it, and splices new text
into the original string. No hand-written YAML parser. Offsets are character offsets
into the decoded text, which holds for `\r\n` files and a leading byte-order mark (both
checked against PyYAML here).

Measured position quirks the design must work around (each checked against PyYAML in
this repository's environment):

- **Block collections** (a list or mapping written one item per line): the end mark
  lies at the start of the next token, *after* any comment lines that follow. The end
  of a block list is therefore the end of the line holding its last item.
- **Nulls written as nothing** (`taxonomy:` followed only by comment lines, or
  `extends: # note`): the value is a zero-width null at the position right after the
  colon.
- **Block scalars** (`key: |` or `key: >-`): the end mark runs to the start of the next
  line, including trailing blank lines.
- **Aliases** (`tags: *x`): the alias node *is* the anchored node, so its marks point at
  the anchor's text elsewhere in the file.

### What each edit does

Let *section* be the top-level key (`taxonomy`, `capabilities`, `work`) and *key* the
key inside it (`extends`, `tags`, `path`).

**Set a list, when the key already holds a list.** Let *old* be the stored list and
*new* the list the writer computed. The edit is **incremental** when both lists are free
of duplicates and the items they share appear in the same relative order in both. Then
only the items added or removed are touched:

- `extends add` appends one item; `extends rm` removes one; `tags add|rm` on a stored
  list that is already sorted inserts or removes items at their sorted places.
- In a block list, a removed item's line is deleted, including any comment at the end of
  that line; an added item gets a new line after the item that precedes it in *new*
  (or before the first surviving item), at the dash column of the existing items.
  Surviving items, their end-of-line comments, and full comment lines between items are
  untouched.
- In a flow list on one line (`[a, b]`), the item and one adjoining `, ` separator are
  inserted or removed.
- An item that spans more than one line, or a flow list that spans more than one line
  and contains a comment, is refused.

When the edit is **not incremental** — for example a hand-edited, unsorted `tags` list
that the writer re-sorts, or a list with duplicates — the whole list is replaced (in its
existing style and dash column) **only if no comment lies within the list's lines**;
otherwise the edit is refused.

**Set a list, when the key is absent.** The key is inserted on the line after the end
of the section's last entry, at the column of the section's existing keys, so comment
lines between that entry and the next top-level key stay where they were. A list is
written in block style, dashes one indent unit deeper than the key.

**Set a value, when the key holds a null.** An explicit null token (`null`, `~`) is
replaced in place. A null written as nothing is replaced by inserting the new block at
the **end of the line holding the key**, so a comment on that line stays on it: for
`extends: # note` the result is `extends: # note` followed by the new item lines; for a
section stub `taxonomy:` followed by commented lines, the new key lines go directly
under `taxonomy:` and the commented lines stay below them.

**Set a string** (`<component>.path`). A single-line plain or quoted scalar is replaced
in place; a comment after it on the same line is kept. A block scalar or a multi-line
scalar as the target is refused.

**Section absent.** `section:` and the key are appended at the end of the document —
before a terminal `...` document-end line if there is one — preceded by a line break if
the file does not end with one.

**Remove a key** (`extends` emptied). The key's lines — key line through the end of its
last value line — are deleted. If that leaves the section with no entries, the
section's own line is deleted too. Comment lines above the key stay.

**Set `id`.** An `id` whose value is null is replaced as above. Otherwise `id: <id>` is
inserted as a new line before the first top-level key — after any leading comment
block, directives and `---` line; in a file with no keys, at the end of the document
as for an absent section.

**Indent unit** (for a new key's list): the gap between the section's column and its
keys' column when the section has block entries; otherwise the same gap measured from
the first top-level block mapping in the file; otherwise 2.

**Scalars** (project ids, tags, paths) are written plain when YAML reads them back as
the same string, and quoted otherwise.

### Sections and keys that are not what the writer expects

| Shape                                          | extends add/rm                  | tags add/rm                                                                   | init path                                                         | id                  |
| ---------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------- |
| section absent                                 | append (add); no-op (rm is refused earlier, "no such extends") | append                                                                        | append                                                            | —                   |
| section null (`work:` with nothing, or `~`)    | edit as a null                  | edit as a null                                                                | edit as a null                                                    | —                   |
| section a non-null non-mapping (`work: docs/work`) | refused, as today (`fs.py:1787-1793`) | **refused** (today: silently replaced, `fs.py:5794-5796`)                     | **refused** (today: silently replaced, `fs.py:1080-1083`)         | —                   |
| section a flow mapping (`{path: x}`)           | refused if a key must be added or removed; an existing key's value may be replaced | same                                                                          | same                                                              | —                   |
| key holds a non-list (`tags: a`)               | refused, as today (`_extends_ids`) | **refused** (today: silently replaced)                                        | —                                                                 | —                   |
| top level a flow mapping                       | refused                         | refused                                                                       | refused                                                           | refused             |
| target value is an alias, or carries an anchor | refused                         | refused                                                                       | refused                                                           | refused             |

The three newly refused shapes are behavior changes and are named in the changelog.
Each was a case where TCW silently discarded what the user had typed.

### Verification

An edit is written only when **both** hold:

1. **Same meaning.** The new text, parsed with the loader `load_config` uses
   (`fs.py:1208-1226`, rejecting duplicate keys), equals the intended mapping.
2. **Confined to its spans.** Every edit declares the span of the original text it
   replaces (for an insertion, a zero-width span). The new text must equal the original
   with exactly those spans replaced: every character outside them is unchanged. A span
   may contain no anchor (`&name`), and no comment other than the end-of-line comment of
   a removed list item or the comments inside a list being replaced whole (which the
   rules above only allow when there are none). The first condition alone would miss a
   lost comment, or an edit that changed an anchor's text and so every alias to it.

A target whose value node starts outside its own key's text (an alias, whose marks
point at the anchor) is refused before any span is computed.

### Refusal messages

A refusal is a `ValueError`, which every calling command already prints as a one-line
`tcw <cmd>: …` error. It names the file and the key path, says why, and gives
instructions that cannot lead to a duplicate section or erased siblings:

- **Key to add or change, section exists:** "under the existing `taxonomy:` section
  (do not add a second one), set: `extends: [acme-shared, other]`" — the full new value
  in flow style on one line, so it is correct at any indentation.
- **Section absent:** the complete block to append at the end of the file.
- **Removal:** "delete the `extends` key and its list from the `taxonomy:` section,
  leaving its other keys" — plus "then the now-empty `taxonomy:` line" only when the
  section would be left empty.
- **Flow section:** "inside the braces of `taxonomy: {…}`, add `, extends: [acme-shared]`"
  — the addition only, never a restated section that could drop a sibling.

### Order of work in `init`

`init` computes one combined edit — `id` (when missing) plus every `<component>.path` —
from one read of the file, and verifies it inside its existing pre-flight, which already
decides every refusal before anything is written (comment at `fs.py:955-959`). Only a
verified edit reaches the write phase, where the config is written once, at the point
`write_sentinel` is called today (`fs.py:1073`), before any folder is deleted
(`fs.py:1076-1077`) or created. A refusal therefore leaves the config, the git index and
every folder — including the default store it would have replaced — exactly as they were.
`write_sentinel` keeps its signature for its 22 direct callers in tests and uses the same
edit routine.

### `_persist_extends` updates memory only after the write

`self.config` is updated after `_write_node_config` returns, not before (today
`fs.py:1778-1781` runs first), so a refused write leaves the store object agreeing with
the file.

### Documentation to change

- `docs/migration-guide-2.4.X-to-2.5.0.md:105-110` ("One more thing: writing the key
  re-renders the file") — replace with the new behavior; the guide's recommendation of
  the `extends` commands (`:62-68`) stays.
- `skills/configure/references/projects.md:104-107` — drop the "re-renders" note.
- The docstrings of `_write_node_config` (`fs.py:1834-1836`) and `_write_tags`
  (`fs.py:5773-5775`) that accept the loss.
- `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` for v2.5.1,
  including the three newly refused shapes.
- The three capability statements under Capability changes.

## Acceptance criteria

Each is checked by an automated test unless it says otherwise. "Byte for byte" means
comparing the file's raw bytes before and after (read in binary), outside the lines
named as changing. Every refusal criterion also checks that the file's bytes and
`git diff --cached` are unchanged.

1. On a file with a leading comment block, 4-space indentation, a comment line inside
   `work.lifecycle`, a long quoted string, and `taxonomy:` holding only `path:`,
   `tcw taxonomy extends add <id>` (against a registered project with `docs/taxonomy/`)
   only adds `extends:` and its item line inside `taxonomy:`, at 4-space indentation.
   The rest is unchanged byte for byte.
2. `tcw capabilities extends <id>` on a file with no `capabilities:` section only appends
   `capabilities:` and its `extends` lines; on a file ending in a `...` line they go
   before it.
3. With a block `extends` list of `a` (with an end-of-line comment), a full comment line,
   then `b` (with an end-of-line comment): `extends add c` adds only a `c` line after
   `b`; `extends rm a` deletes only `a`'s line, and `b`'s comment and the full comment
   line survive. Removing the last id deletes the `extends` lines, and the `taxonomy:`
   line only if nothing else is left in it; comment lines above `extends` stay.
4. `tcw work tags add <tag>` on a sorted flow list inserts the item at its sorted place
   in the same line; on a sorted block list with per-item comments, inserts one line and
   keeps every comment; `tags rm` removes only that item's line. Where `work:` has no
   `tags`, it is inserted without touching `work:`'s other keys.
5. `tcw work tags add <tag>` for an already-registered tag leaves the file byte-identical
   and stages nothing.
6. On an unsorted block `tags` list with no comments, `tags add` replaces the list with
   the sorted one and changes nothing outside it; on the same list with a comment inside
   it, `tags add` is refused.
7. A comment line directly after a replaced or extended block list (before the next key)
   survives.
8. `extends add` on a stub `taxonomy:` whose only children are comment lines, and on
   `extends: # note`, keeps every comment: the note stays on the `extends:` line and the
   commented lines stay below the inserted lines.
9. A `\r\n` file keeps `\r\n` on every line, including inserted ones, and a file starting
   with a byte-order mark keeps it — both checked on raw bytes. A file without a trailing
   line break gets the new key on its own line.
10. `tcw init --work-path <dir>` on an existing commented config without `id` writes the
    `id` line and the `work.path` line and changes nothing else; a comment after an
    existing `path` value on its line survives when the path is replaced.
11. `tcw init --work-path <dir>` where the edit is refused (for example `work: {tags: [a]}`
    in flow style, needing `path` added) exits non-zero and leaves the config bytes, the
    git index and the scaffold unchanged: the default `docs/work/` store is still
    present, no new folder exists, and no `id` was written.
12. A fresh `tcw init --id <id>` with no `tcw-config.yaml`, and with an empty one,
    succeeds and writes the file in full.
13. `write_sentinel` on a commented file without `id` inserts one `id:` line below the
    leading comment block; on a file with `id: null` it replaces the value, the file then
    parses with `id` equal to the given project id, and a comment elsewhere survives.
14. `tcw taxonomy extends add <id>` on `taxonomy: {path: docs/t}` is refused with a
    message containing `, extends: [<id>]` and the words "inside the braces".
15. An `extends rm` whose removal would edit an anchor that is aliased elsewhere
    (`extends: &ids [a, b]` with `*ids` used elsewhere) is refused; `tags add` where
    `work.tags` is an alias (`tags: *x`) is refused.
16. `tcw init --path` where the existing `taxonomy.path` is a block scalar is refused.
17. `tcw work tags add` with `work: docs/work`, and `tcw init --work-path` with
    `work: docs/work`, are refused, and their messages name `work` and the file.
18. After a refused `extends add`, the same store object's `config` still lacks the new
    id, and a second, valid `extends add` on a fixed file writes only its own id.
19. For each writer and a table of input shapes, the parsed mapping after a successful
    edit equals what today's whole-file rewrite produces for the same input, except the
    `id: null` case (criterion 13).
20. The refusal message for a removal the file cannot take does not contain a complete
    `taxonomy:` block, and the message for a key added to an existing block section says
    not to add a second section.
21. `pyproject.toml`'s runtime dependencies are unchanged (`PyYAML` only) — checked by
    reading the diff.
22. `grep -rn "re-render" docs/migration-guide-2.4.X-to-2.5.0.md skills/` returns
    nothing, and no docstring in `tcw/store/fs.py` still says comments are dropped when
    the node config is written — checked by reading the diff.
23. The full test suite passes when run as CI runs it (bare `pytest`).

## Risks

- **Text-splicing bugs corrupt a user's file.** Mitigated by the two-part verification:
  a wrong edit either changes the meaning (caught by condition 1) or touches text outside
  its spans (caught by condition 2), and either refuses. The residual risk is an edit
  that is confined and correct in meaning but badly laid out (an odd indent on an
  inserted line). Criteria 1-10 guard the shapes.
- **Commands that worked before now refuse.** Flow-style sections and top levels that
  need a key added or removed, unsorted commented tag lists, aliases, block scalars, and
  the three newly refused non-mapping shapes. All are rare in hand-written config, each
  message gives the fix, and each was previously silent data loss.
- **PyYAML position behavior is not a documented contract.** The four quirks were
  measured, not read from documentation. Criteria 7, 8, 15 and 16 pin them, so a PyYAML
  change that moves them fails a test rather than a user's file — and the span check
  refuses rather than writes if one slips through.
- **`init` now writes `work.path` before replacing the default store rather than after.**
  If deleting the old store then fails, the config already names the new location. The
  same was already true of `id`, and the pre-flight has already confirmed the old store
  is pristine (`fs.py:1001-1006`), so nothing is lost; re-running `init` completes it.

## Notes

- The `request` stage questions were not asked of the requester for this item
  (autonomous run; see `initial-request.md`). Its two marked assumptions are adopted:
  scope is every writer of the node config (extended by the sweep to `init`'s
  `<component>.path` and `write_sentinel`), and the migration guide keeps recommending
  the `extends` commands.
- The `id: null` defect in `write_sentinel` is folded in because the same function's
  write is being replaced; it follows from computing the intended mapping correctly.
- Revised after Codex and Opus review. Settled with the lead: refuse rather than rewrite;
  missing and empty files are written in full; list edits are incremental where the
  lists allow, otherwise whole-list replacement only when the list holds no comments.

## Open questions

None.
