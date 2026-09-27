# Spec: Read item tags normalized and keep non-tag work.tags entries visible

## Capability changes

- **Changed** `work/tag-a-work-item` (`cap-609d75`):
  - an item's tags are read in their canonical form, so a tag written by hand as
    `CLI` in `state.yaml` is the tag `cli` everywhere it is read;
  - `tcw work tags add` / `rm` refuse, naming the entry, while `work.tags` holds
    an entry that is not a tag, instead of silently dropping it;
  - the description's sentence saying a `when:` condition "is matched as
    written", and that a quoted `"cli,docs"` there "matches nothing", is out of
    date since the unreleased
    `2026-09-15-report-malformed-keys-and-unregistered-tags-in-lifecycle-config`
    (conditions are normalized, and a comma is a reported problem). It is
    corrected here.

## Problem

1. **An item's tags are read exactly as stored.** `FsWorkStore` builds
   `WorkItem.tags` with `tags=list(state.get("tags") or [])`
   (`tcw/store/fs.py:4972`). Every writer normalizes (`_validate_tags`,
   `tcw/store/fs.py:6503-6518`), so only a hand edit produces a non-canonical
   tag. But the unreleased change named above now normalizes lifecycle
   conditions when parsing them (`tcw/store/base.py:2337-2339`), and
   `Condition.matches` compares the two sets directly
   (`tcw/store/base.py:1151-1155`). An item hand-tagged `CLI` therefore no longer
   matches a condition written `CLI`, which it did in v2.6.2; the stage rules
   bound to that condition are skipped for it without a word.
   `docs/changelogs/upcoming.md` currently lists this as a known behavior
   change.

   Reproduced on main (2026-09-27): an item whose `state.yaml` says
   `tags: [CLI]` reads as `['CLI']`, the condition `{tags: [CLI]}` does not
   match it, and `check` reports `unregistered tag 'CLI'` although `cli` is
   registered.

   The same raw read also affects, today and in v2.6.2:
   - `tcw work list --tag cli` (the filter is normalized, `tcw/work/cli.py:86`,
     the item side is not, `tcw/work/cli.py:927`), which misses the item;
   - `tcw work edit --untag cli` (`tcw/work/cli.py:2463-2464`, normalized
     argument against raw item tags), which does not remove `CLI`;
   - the tracker's issue type (`TrackerCreate.type_for`,
     `tcw/store/base.py:1230`), where a hand-written `Bug` does not select the
     bug type;
   - `tcw work show` and `list`, which `', '.join(item.tags)`
     (`tcw/work/cli.py:211`, `953`) and would raise on a non-string tag such as a
     bare YAML `7`. A non-list `tags: CLI` is read by `list()` as the three tags
     `C`, `L`, `I`.

2. **`tags add` / `rm` silently drop a non-tag entry of `work.tags`.**
   `_registered_tag_entries` (`tcw/store/fs.py:6009-6024`) sets aside an entry
   such as `7` and `check` reports it (`tcw/store/fs.py:6524`). But
   `register_tags` / `unregister_tags` build the new list from
   `registered_tags()` (`tcw/store/fs.py:6495-6501`), and `_write_tags`
   (`tcw/store/fs.py:6455-6493`) writes it back, so the entry disappears.
   Reproduced on main: with `work.tags: [cli, 7]`, `tags add docs` leaves
   `[cli, docs]`.

## Goals

1. Every read of an item's tags returns them normalized, with duplicates
   removed and first-seen order kept, so every comparison against a condition,
   a filter, an `--untag` or the tracker's bug type agrees with the
   normalized side.
2. A tag that cannot be normalized — a non-string, one holding a comma, one
   that normalizes to nothing — is still read, as its text, so `check` keeps
   reporting it as an unregistered tag and no command raises on it. A
   non-list `tags:` value is read as one entry, not split into characters.
3. A `work.tags` entry holding a comma is not a tag, as a comma already is in a
   condition (`tcw/store/base.py:2330-2335`) and a plan stage
   (`tcw/store/fs.py:4754-4757`). Today `_registered_tag_entries` normalizes
   `"cli,docs"` into the one tag `cli-docs` without a word.
4. `tcw work tags add` and `tcw work tags rm` refuse while `work.tags` holds an
   entry that is not a tag. The refusal names the entry and says to fix or
   remove it in `tcw-config.yaml`; the file is left unchanged.

## Non-goals

- Rewriting existing `state.yaml` files into canonical form. The read is
  canonical; the next write of the item's tags stores the canonical form, as
  it does today.
- A separate `check` problem for a non-canonical spelling (`CLI`). Once it is
  read as `cli`, it is the registered tag, and there is nothing to fix.
- A shape check for other `state.yaml` fields.
- Keeping a non-tag `work.tags` entry through a rewrite. `config_edit.SetList`
  writes strings only (`tcw/store/config_edit.py:52-55`), and a round-trip of an
  arbitrary YAML value is not worth building for a hand-edit mistake that
  `check` already reports.

## Design

- **One reading rule, in the base module.** Add `read_tags(raw) -> list[str]` to
  `tcw/store/base.py`, beside `normalize_tag`, so any store reads an item's tags
  the same way. `None` or empty gives `[]`; a non-list value is treated as a
  one-element list. Each element that is a string without a comma and
  normalizes goes in normalized; any other element goes in as `str(element)`
  unchanged, which `check` then reports as an unregistered tag. Duplicates are
  dropped, first-seen order kept.
  - It stays in the model: a non-filesystem store reads tags too, and must
    agree with conditions that are already normalized.
- **The filesystem item read uses it** (`tcw/store/fs.py:4972`). Nothing else
  changes at the call sites listed under Problem: each already compares against
  normalized values, so it now agrees.
- **`_write_tags` refuses on a non-tag entry**, before the no-op comparison,
  using the second half of `_registered_tag_entries()`:
  `"<config path>: work.tags entry 7 is not a tag; fix or remove it by hand,
  then run this again"`. This is the same function that already refuses a
  `work.tags` that is not a list (`tcw/store/fs.py:6483-6485`); both `add` and
  `rm` go through it, so one guard covers both. It raises `ValueError`, which the
  CLI already reports (`tcw/work/cli.py:3821-3823`, `3851-3853`).
  - Refusing, rather than dropping with a warning, keeps the entry and says so,
    which the request allowed ("keep it" or "say so"). Registering a tag while
    the registry itself is malformed is the case `check` already flags.
- **`_registered_tag_entries` sets aside an entry holding a comma**, beside the
  non-string case, so it is reported by `check` and refused by goal 4.
- **Documentation.** Remove the "hand-edited into a non-canonical form (`CLI`)
  no longer matches" clause from `docs/changelogs/upcoming.md`, and add Fixed
  entries to the changelog and release notes. The Fixed entry also says that a
  hand-written `Bug` now selects the tracker's bug issue type
  (`TrackerCreate.type_for`, `tcw/store/base.py:1230`), and that `list`, `show`
  and the web app display the canonical spelling. Update the capability description
  as listed above.

## Acceptance criteria

1. An item whose `state.yaml` holds `tags: [CLI, cli, Docs Only]` reads as
   `['cli', 'docs-only']` from `FsWorkStore.get` and from `query`.
2. With `cli` and `docs-only` registered, a condition `{tags: [CLI]}` matches that item, and
   `check` reports no tag problem for it.
3. `tcw work list --tag cli` lists that item, and `tcw work edit <slug>
   --untag cli` removes the tag from its `state.yaml`.
4. An item with `tags: [7, "cli,docs", "!!!"]` reads as
   `['7', 'cli,docs', '!!!']`; `tcw work show <slug>` exits 0; `check` reports
   `unregistered tag` for each of the three (none are registered).
5. An item with `tags: CLI` (a string, not a list) reads as `['cli']`.
6. With `work.tags: [cli, 7]`, `tcw work tags add docs` exits 1, its message
   names the entry `7`, and `tcw-config.yaml` is byte-for-byte unchanged.
   `tcw work tags rm cli` behaves the same way.
7. With `work.tags: [cli]`, `tags add docs` and `tags rm docs` still work as
   before.
9. With `work.tags: [cli, {a: 1}]` (a mapping entry), `tags add docs` exits 1
   with the same refusal rather than a `TypeError` traceback, which is what it
   does today (`set(current)` at `tcw/store/fs.py:6487`).
10. With `work.tags: [cli, "cli,docs"]`, `check` reports the entry `'cli,docs'`
    as not a tag, and `tags add docs` refuses as in criterion 6.
8. `docs/changelogs/upcoming.md` no longer says a hand-edited non-canonical tag
   stops matching, and the `work/tag-a-work-item` description no longer says a
   condition is matched as written.

## Risks

- **A hand-written tag that no condition matched before now matches one.** An
  item hand-tagged `Docs` matches `not_tags: [docs]` and is excluded where, in
  v2.6.2, it was not. That is the reading the tag registry already uses, and it
  goes in the changelog as a fix.
- **A registry with a stray entry now blocks `tags add` / `rm`** until it is
  fixed by hand. The message says exactly what to remove, and `tcw validate`
  already reports the same entry.
- **Sweep.** Searched `tcw/` for every read of an item's `tags`
  (`grep -rn "\.tags\b"` and `state.get("tags")`): the filesystem item read at
  `tcw/store/fs.py:4972` is the only place an item's tags are built from stored
  data; plan-stage tags (`tcw/store/fs.py:4750-4761`) and condition tags are
  already normalized. The web app reads items through the same store.

## Notes

- Spec review (adversarial-spec-reviewer, 2026-09-27): criteria 2 and 3 were
  wrong as first written — the fixture registered only `cli`, so `docs-only`
  made `check` report a problem and `--untag cli` refuse. Fixed. Also adopted
  from it: criterion 9 (a mapping entry crashes `tags add` today), the comma rule
  for registry entries (goal 3, criterion 10) and the changelog line on the
  tracker bug type.

- The choice to refuse rather than keep or warn (goal 4) is mine; the user can
  overrule it at review.
