# Plan — Derive an accepted inbox item's title from the entry's H1 and strip the date prefix

Four code tasks, then one documentation block. Every method is named by
**symbol**; line numbers are navigation hints only, because three sibling items
land in `tcw/store/fs.py` before this one (see `## Notes`).

Tasks 1-4 each leave `python -m pytest` green at their commit boundary. Baseline
on the tree today: **1763 passed**.

---

## Task 1 — Bound `FsWorkStore._unique_slug`'s output

Fixes a defect reachable **today**, independently of the title change, so it goes
first: `tcw work new` crashes or produces a degenerate slug right now.

### Files

- `tcw/store/fs.py` — `FsWorkStore._unique_slug` (currently `:2441-2446`)
- `tests/test_work.py` — new tests appended (this file already owns
  `tcw work new` and store-creation behavior)

### Change

`_unique_slug` computes the slug body once, with two bounds, then runs its
existing collision loop unchanged:

```python
def _unique_slug(self, created: str, title: str) -> str:
    # ponytail: 120 chars, not a computed budget. A path component holds 255
    # bytes; the date prefix costs 11, `mkdtemp(prefix=f".{slug}-")`
    # (inbox_accept) costs 10 more, and the collision suffix a few — so 120
    # leaves >100 bytes spare. Raise it if a real title ever gets clipped.
    body = slugify(title)[:120].rstrip("-") or "untitled"
    base = f"{created}-{body}"
    slug, n = base, 2
    while self._find(slug) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug
```

Three decisions, stated so nobody re-derives them:

- **The cap is 120 characters, and characters *are* bytes here.** `slugify`
  (`tcw/store/fs.py:640-641`) substitutes every run outside `[a-z0-9]` with `-`,
  so its output alphabet is exactly `[a-z0-9-]` — pure ASCII, one byte per
  character. No `encode`/`decode` round trip is needed to bound bytes, and
  adding one would be ceremony. Longest slug body in this repo's own
  `docs/work/` today: 97 characters, so nothing real is clipped.
- **`rstrip("-")` runs after the cut**, so truncating mid-word never leaves a
  trailing hyphen. It runs *before* the `or "untitled"` so a body that is all
  hyphens also falls through to the default.
- **Empty → `"untitled"`.** Two such items collide, and the *existing* loop
  makes the second `<date>-untitled-2`. No new collision logic.

Nothing else in the method changes. `create_work` and `inbox_accept` both route
through it and both inherit the fix — which is the point: guarding only
`inbox_accept` would leave `tcw work new` broken.

### Proof

New tests in `tests/test_work.py`, using the existing `node()` helper
(`tests/test_work.py:15`) and `from tcw.cli import main`:

| test | asserts |
| --- | --- |
| `test_work_new_survives_a_title_that_slugifies_to_nothing` | `main(["work", "new", "東京"])` returns `0` and creates `docs/work/backlog/<today>-untitled/`. **Fails today**: produces `<today>-` (verified in a scratch node). |
| `test_work_new_disambiguates_repeated_untitled_slugs` | the same call twice yields `<today>-untitled` then `<today>-untitled-2`. **Fails today**: yields `<today>-` then `<today>--2`. |
| `test_work_new_survives_a_very_long_title` | `main(["work", "new", "a" * 300])` returns `0`; the created directory name is `len == 131` (11 date + 120 body). **Fails today**: uncaught `OSError: [Errno 63] File name too long`, verified in a scratch node. |
| `test_work_new_keeps_the_full_title_when_the_slug_is_truncated` | for that same 300-character title, `state.yaml`'s `title` is the full 300 characters — only the slug is bounded. |
| `test_work_new_punctuation_only_title` | `main(["work", "new", "!!! ???"])` returns `0` and creates `<today>-untitled`. |
| `test_work_new_ordinary_title_is_unchanged` | `main(["work", "new", "Another Raw Request"])` still yields `<today>-another-raw-request`. Guards against the cap or the default firing on normal input. |

Covers spec criteria **16, 17, 18** and the slug half of **14, 15**.

`python -m pytest` green: yes — `_unique_slug`'s output for every existing
title is byte-identical (no existing title is empty, all-punctuation, or over
120 slugified characters).

---

## Task 2 — Add the heading scan to `tcw/store/base.py`

The only non-trivial new logic in the item. It lands **isolated and fully
tested before anything calls it**, so Task 3 is pure wiring.

### Files

- `tcw/store/base.py` — two new module-level functions
- `tcw/store/fs.py` — `FsWorkStore._frontmatter` refactored to use one of them
- `tests/test_inbox_title.py` — **new file**

### Where it lives, and why

`tcw/store/base.py`, as module-level functions beside the ones already there —
`normalize_tag` (`:506`), `resolution_status` (`:471`), `topo_order` (`:1336`).
This is the spec's litmus verdict realized: reading a title out of an item's
body is storage-neutral, so a second adapter inherits it rather than
reimplementing it. `fs.py` imports `base.py` (`tcw/store/fs.py:30`) and
`base.py` imports nothing from `tcw.store`, so this direction is the only one
available anyway.

**`tcw/store/base.py` gains exactly two functions and no class, no ABC method,
no new abstract operation.** The abstract `WorkStore.inbox_accept` docstring
gains its derivation contract in Task 3, where the behavior it describes is
actually wired.

```python
def frontmatter_end(content: str) -> int:
    """Offset just past a leading ``---`` YAML block, or 0 when there is none.

    The **single** definition of "leading frontmatter" in TCW:
    ``FsWorkStore._frontmatter`` parses the block this delimits, and
    ``body_title`` skips it. Two definitions would drift.
    """
    if not content.startswith("---\n"):
        return 0
    end = content.find("\n---\n", 4)
    return 0 if end < 0 else end + 5


_FENCE = re.compile(r"^(`{3,}|~{3,})")


def body_title(body: str | None) -> str | None:
    """The first ATX H1 in ``body``, or None.

    Skips leading frontmatter and fenced code blocks; a fence closes only on
    the same delimiter character with a run at least as long as the opener, so
    a three-backtick line inside a four-backtick fence does not end it.
    """
    if body is None:
        return None
    fence = None
    for line in body[frontmatter_end(body):].splitlines():
        match = _FENCE.match(line.strip())
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
            continue
        if match:
            fence = match[1]
        elif line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return None
```

`base.py` already imports `re` (used by `normalize_tag`); no new import.

### The `_frontmatter` refactor

`FsWorkStore._frontmatter` (`tcw/store/fs.py:2296`, predicate at `:2303`,
boundary at `:2305`) stops computing the boundary itself:

```python
if not content.startswith("---\n"):
    return None
end = frontmatter_end(content)
if end == 0:
    raise ValueError(f"{label}: malformed YAML frontmatter")
metadata = yaml.safe_load(content[4:end - 5])
```

`end - 5` is exactly the old `content.find("\n---\n", 4)`, so the parsed slice
is unchanged and every existing `_frontmatter` behavior — including the raise
on an unterminated block — is preserved. `frontmatter_end` joins the existing
`from tcw.store.base import (...)` block at `tcw/store/fs.py:30`.

This is what makes the parity a fact rather than a promise: there is one
predicate, in one function, and both callers use it.

### Proof — `tests/test_inbox_title.py`

A new focused file, following `tests/test_work_tags.py`'s pattern (a small file
per concern, importing the helper it tests from `tcw.store.base`). No fixtures,
no `node()` needed — `body_title` is pure.

Nineteen named assertions. Each row is one `assert` in a table-driven test or a
one-line named test; the implementer writes them from this table, not from the
spec.

**Basic shapes**

| # | input | expected |
| --- | --- | --- |
| 1 | `"# Another Raw Request\n\nBody.\n"` | `"Another Raw Request"` |
| 2 | `"Just body text, no heading.\n"` | `None` |
| 3 | `None` (binary primary resource) | `None` |
| 4 | `"## Sub\n\n# Real\n"` | `"Real"` — `##` is not an H1 |
| 5 | `"#\n\n#   \n\n# Real\n"` | `"Real"` — an empty heading is not a match |
| 6 | `"# Support C#\n"` | `"Support C#"` — no ATX-closing mangling |
| 7 | `"# Fix auth #\n"` | `"Fix auth #"` — closing sequence kept literally |
| 8 | `"  # Indented\n\n# Real\n"` | `"Real"` — a heading must start at column 0 |

**Frontmatter (parity with `_frontmatter`)**

| # | input | expected |
| --- | --- | --- |
| 9 | `"---\nfrom: parent\ninitiative: e\n---\n\n# Do the thing\n\ndetails\n"` (the `_inbox_write` shape) | `"Do the thing"` |
| 10 | `"---\r\nfrom: parent\r\n---\r\n\r\n# CRLF Title\r\n"` | `"CRLF Title"` — not frontmatter per `_frontmatter`, so the whole body is scanned and the H1 still wins |
| 11 | `"﻿---\nfrom: p\n---\n\n# BOM Title\n"` | `"BOM Title"` — same reason |
| 12 | `"---\n\n# Swallowed\n\n---\n\n# Real\n"` | `"Real"` — a leading thematic break is treated as frontmatter and swallows the first H1. **Documented miss, asserted so it stays deliberate.** |
| 13 | `"---\nfrom: p\n---"` (unterminated) | `None` — `frontmatter_end` returns 0, whole body scanned, no H1. Unreachable through `inbox_accept`, which raises at `_inbox_initiative` first; asserted at the unit level anyway. |

**Fences**

| # | input | expected |
| --- | --- | --- |
| 14 | ` ```sh\n# shell comment\n```\n\n# Real\n` | `"Real"` — fenced content skipped |
| 15 | ` ```sh\n# only a comment\n```\n` | `None` — falls through to the caller's fallback |
| 16 | ` ````\n# Example inside documentation\n```\n# Still inside the four-backtick fence\n````\n\n# Real request title\n` | `"Real request title"` — **the run-length case**. A bare toggle returns `"Still inside the four-backtick fence"`; this assertion is the one that fails if the run length is dropped. |
| 17 | ` ```\n~~~\n# not a title\n```\n\n# Real\n` | `"Real"` — a tilde run cannot close a backtick fence |
| 18 | `"~~~\n# in tilde fence\n~~~\n\n# Real\n"` | `"Real"` — tilde fences work symmetrically |
| 19 | ` ```sh\n# comment\n\n# Real\n` (unclosed) | `None` — an unclosed fence suppresses every later heading; the safe direction, asserted so the behavior is chosen rather than incidental |

Plus one parity test, which is what actually prevents drift:

| test | asserts |
| --- | --- |
| `test_frontmatter_end_agrees_with_the_frontmatter_parser` | for each of rows 9-13's bodies, `frontmatter_end(b) != 0` **iff** `b.startswith("---\n") and b.find("\n---\n", 4) >= 0`, and `FsWorkStore._frontmatter` either returns/raises consistently with that predicate. One place defines the boundary; this proves the other caller did not fork it. |

`python -m pytest` green: yes — `body_title` has no callers after this task, and
the `_frontmatter` refactor is behavior-preserving (the initiative tests at
`tests/test_work.py:341-388` cover it).

---

## Task 3 — Wire the derivation into `FsWorkStore.inbox_accept`

Pure wiring: the risky logic is already tested.

### Files

- `tcw/store/fs.py` — `FsWorkStore.inbox_accept` (currently `:2995`), plus a
  module-level `_DATE_PREFIX` constant beside `slugify`
- `tcw/store/base.py` — `WorkStore.inbox_accept` docstring (`:1545`)
- `tests/test_work.py` — new tests appended

### Change

Beside `slugify` (`tcw/store/fs.py:640`):

```python
_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")
```

In `inbox_accept`, replacing the single line `accepted_title = (title or
detail.entry.title).strip()` (`:3002`) — everything before it (the
`_resolve_inbox_ref`, `_inbox_path`, `_inbox_detail` and `_inbox_initiative`
calls) and everything after it is untouched:

```python
label = _DATE_PREFIX.sub("", detail.entry.title).strip() or detail.entry.title
accepted_title = (title or body_title(detail.body) or label).strip()
if not accepted_title:
    raise ValueError("title is required and must be non-empty")
created = date.today().isoformat()
# Slug from the label when the title has no ASCII to slugify — the H1 stays
# the title, but `<date>-untitled` is a worse identifier than the filename.
slug = self._unique_slug(created, accepted_title if slugify(accepted_title) else label)
```

Pinned behaviors, all from the spec:

- **Precedence**: `--title` → H1 → date-stripped label. `--title ""` is falsy
  and falls through to derivation, exactly as today.
- **`_DATE_PREFIX` is shape, not calendar validity** — `2026-13-45-foo` strips.
  The trailing hyphen is part of the pattern, so `2026-08-19.md` keeps the
  title `2026-08-19`.
- **`or detail.entry.title`** keeps the unstripped label when stripping empties
  it (a file literally named `2026-08-19-.md`), rather than raising on an entry
  that does have a name.
- **The slug rule does not change**: `<acceptance-date>-<slugified-title>`. The
  entry's own dated stem is never reused as the slug.

`body_title` and `slugify` are already in scope in `fs.py` (the former joins the
`from tcw.store.base import (...)` block at `:30`).

`WorkStore.inbox_accept`'s docstring (`tcw/store/base.py:1545`) becomes:

```python
@abstractmethod
def inbox_accept(self, ref: str, title: str | None = None) -> WorkItem:
    """Atomically consume raw intake into a new backlog work item.

    The title is `title` when given, else the first ATX H1 the entry's body
    declares (`body_title`), else a store-provided label for the entry. The
    body read is the contract; how a store labels an entry is its own
    business.
    """
```

That is the whole store-interface delta — a documented precedence, no signature
change, no new abstract method.

### Proof

New tests in `tests/test_work.py`, beside the existing inbox tests. Every one
uses the existing `node()` helper.

**The report**

| test | asserts |
| --- | --- |
| `test_inbox_accept_derives_the_title_from_the_h1` | entry `2026-08-19-another-raw-request.md` with first line `# Another Raw Request`, accepted with no `title=`, gives `state.yaml` `title: Another Raw Request` and slug `<today>-another-raw-request`; the folder is `docs/work/backlog/<today>-another-raw-request/`. Spec criterion 1. |
| `test_inbox_accept_finds_the_h1_after_frontmatter` | the `_delegated` shape gives `Do the thing`, not `req` and not the dated stem. Spec criterion 2. |
| `test_inbox_accept_reads_a_folder_index_h1` | folder entry with `INDEX.md` declaring `# Folder Request Title` → that title; the same content as `INDEX.txt` → the same title. Spec criterion 3. |
| `test_inbox_accept_strips_the_date_prefix_from_the_fallback` | `2026-08-19-no-heading.md` with no H1 → title `no-heading`, slug `<today>-no-heading`. **One date, not two** — assert the slug does not contain `2026-08-19-2026-08-19`. Spec criterion 4. |
| `test_inbox_accept_ignores_a_heading_inside_a_fence` | an entry whose only `# ` line is inside a ` ```sh ` fence falls back to the filename. Spec criterion 5. |
| `test_inbox_accept_skips_non_h1_and_empty_headings` | `## Sub` then `# Real` → `Real`; `#`/`#   ` then `# Real` → `Real`. Spec criteria 6, 7. |
| `test_inbox_accept_title_override_beats_a_competing_h1` | entry declaring `# A Competing Heading`, accepted with `title="Clean Title"` → title `Clean Title`, slug `<today>-clean-title`. Asserts the *result*, not that no H1 was read. Spec criterion 8. |
| `test_inbox_list_still_shows_the_filename_label` | with that same H1-bearing entry present, `main(["work","inbox","list"])` prints exactly `2026-08-19-another-raw-request.md \| file \| 2026-08-19-another-raw-request`. `InboxEntry.title` must not become the H1. Spec criterion 9. |

**Delegate / escalate and slug construction**

| test | asserts |
| --- | --- |
| `test_inbox_accept_dates_the_slug_when_accepted_not_when_filed` | entry named `2026-08-01-do-the-thing.md` with H1 `# Do the thing` → slug starts with **today's** date and `state.yaml: created` equals it; the slug does not start with `2026-08-01`. No clock freezing needed. Spec criterion 10. |
| `test_inbox_accept_disambiguates_duplicate_delegated_requests` | write `<today>-do-it.md` and `<today>-do-it-2.md`, both with H1 `# Do it` (the pair `_inbox_write`'s own loop at `tcw/work/recursion.py:269-271` produces); accepting both gives titles `Do it`/`Do it` and slugs `<today>-do-it`/`<today>-do-it-2`. Spec criterion 11. |
| `test_inbox_accept_takes_only_the_first_line_of_a_multiline_heading` | body `# Fix auth\nurgently\n` → title `Fix auth`. Pins the accepted limitation. Spec criterion 12. |
| `test_inbox_accept_keeps_an_atx_closing_sequence` | H1 `# Fix auth #` → title `Fix auth #`, slug `<today>-fix-auth`. Spec criterion 13. |

**Slug safety, inbox side**

| test | asserts |
| --- | --- |
| `test_inbox_accept_uses_the_label_when_the_title_has_no_slug` | `2026-08-19-tokyo-request.md` with H1 `# 東京` → title `東京`, slug `<today>-tokyo-request`. Spec criterion 14, first half. |
| `test_inbox_accept_falls_back_to_untitled_when_nothing_slugifies` | an entry whose filename *and* H1 both slugify to empty → title from the H1, slug `<today>-untitled`; a second such entry → `<today>-untitled-2`. Spec criteria 14 (second half), 15. |
| `test_inbox_accept_truncates_a_long_h1_in_the_slug_only` | 300-character H1 → `state.yaml` title is the full 300 characters, the directory name is 131 characters, no `OSError`. Spec criterion 16. |

**Existing behavior that must not move**

| test | asserts |
| --- | --- |
| `test_inbox_accept_degenerate_dated_filenames` | `2026-08-19.md` (no trailing hyphen) with no H1 → title `2026-08-19`; `2026-08-19-.md` with no H1 → title `2026-08-19-`. Neither raises `title is required and must be non-empty`. Spec criterion 19. |
| **`tests/test_work.py:286-287`, unmodified** | this is an *existing* test — `test_inbox_show_and_accept_resolve_listed_file_title` accepts `example.md` with no `title=` and asserts the accepted title is exactly `"example"`. It is the closest existing test to this change and **must pass without being edited**: its body (`"do it\n"`) has no H1, and `example` carries no date prefix, so both new rules are no-ops on it. If it needs editing, stop and investigate — the derivation is doing something this plan did not intend. Spec criterion 21. |
| `tests/test_work.py:229` (`test_inbox_accept_binary_file_does_not_render_binary`), unmodified | `sample.dat` has `body is None`, so `body_title` returns `None` and the stem `sample` is used, as today. Spec criterion 20. |

`python -m pytest` green: yes — spec criteria 22 (`-k inbox`: 21 passed
baseline) and 23 (full suite: 1763 passed baseline) are the check.

---

## Task 4 — Capability ledger

Separate from the docs block because these are ledger records, not prose, and
`tcw validate` gates them.

### Files

- `docs/capabilities/work/manage-the-work-inbox/description.md`
- `docs/capabilities/work/open-a-work-item/description.md`

### Change

`manage-the-work-inbox` gains one sentence after the paragraph beginning
"Inbox entries remain permissive intake packages":

> The accepted item's title is the `--title` I passed, or the first `# ` heading
> the entry's body declares, or the entry's own name with a leading `YYYY-MM-DD-`
> removed — in that order.

`open-a-work-item` gains one sentence after the first: the generated slug is
bounded — a title that reduces to nothing yields `untitled`, and a very long one
is truncated — so no title can produce an unusable slug.

Neither capability's `meta.yaml` changes; both stay `Supported`. Both are the
"Changed" deltas the spec's `## Capability changes` section named.

### Proof

`tcw validate` exits `0`. Spec criterion 25.

---

## Documentation Sync

All four of this project's declared entries (`tcw work docs`) were evaluated.
Three fire; one fires and resolves to reference files.

| entry | trigger | fires? | what changes |
| --- | --- | --- | --- |
| `README.md` | Public-API | **yes** | user-facing behavior changed |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | |
| `skills/<component>/SKILL.md` | Skill-Driven-Component | **yes**, via `tcw-work`'s references | `skills/tcw-work/SKILL.md` itself contains no title guidance (`grep -n "title"` returns nothing); the guidance lives in its `references/`, so that is what changes |

### Files and their edits

1. **`README.md:930`** — "the command does not require or parse that template"
   becomes accurate: the command does not *require* the template, but it does
   read the first `# ` heading of an entry's body as the item's title. Add one
   sentence to the same paragraph naming the precedence
   (`--title` → H1 → filename minus its date prefix). The example block at
   `README.md:812-818` needs no change: `inbox accept request.md` and
   `inbox accept request` still work exactly as commented, and the
   `--title "Clear title"` line is still a valid override.
2. **`docs/work-inbox-template.md`** — two edits, and **the placeholder is a
   decision, not a mention**:
   - Line 1, `# Request title`, becomes `# <one-line title of this request>`.
     **Decision: change the placeholder rather than only warning about it.** A
     user who copies the template and forgets the heading now gets an item
     titled `<one-line title of this request>` — obviously unfinished — instead
     of the plausible-looking `Request title`, which would sit in the backlog
     unnoticed. The angle-bracket form is already how this repo writes
     placeholders elsewhere, and it costs one line.
   - Line 20, "TCW does not parse or require its sections", becomes: TCW does
     not require these sections, but it *does* read the first `# ` heading as
     the accepted item's title — so replace the placeholder above.
3. **`skills/tcw-work/references/stage-inbox.md:42`** — step 5 drops the
   mandatory `--title`: `tcw work inbox accept <entry>` is the normal call, with
   `--title "<clear title>"` named as the override for when the entry's heading
   is missing or poor. This is the workaround TCW has been shipping for the bug;
   removing it is the point of the item.
4. **`skills/tcw-work/references/commands.md:6`** — already writes
   `[--title <t>]` as optional. **Verify only; no edit expected.** If the row
   still reads as it does today, leave it.
5. **`docs/changelogs/upcoming.md`** — under **Fixed**, two entries:
   `inbox accept` derives the title from the entry's H1 and strips the date
   prefix from the filename fallback; `_unique_slug` bounds its output so a
   title that slugifies to nothing or exceeds the path limit no longer produces
   `<date>-` or an uncaught `OSError`. Name `FsWorkStore.inbox_accept`,
   `FsWorkStore._unique_slug` and `tcw.store.base.body_title` — this file is
   technical.
6. **`docs/release-notes/upcoming.md`** — plain language, no module names:
   accepting an inbox entry now names the item after the entry's own heading
   instead of its filename, so the date no longer appears twice and passing
   `--title` is no longer necessary; and creating an item with an unusual or
   very long title no longer fails.

### Proof

`tcw validate` exits `0`; the six files above are re-read against the finished
diff. Spec criteria **24, 26**.

---

## Verification

What the suite cannot check, to be run by hand before `submit`.

1. **The reporter's reproduction, verbatim, against the installed binary.** The
   test suite exercises `FsWorkStore` and `tcw.cli.main` in-process; it never
   proves the shipped console-script entry point behaves the same. In a scratch
   directory outside this repo:

   ```sh
   mkdir tcwtest && cd tcwtest && git init -q .
   printf 'id: tcwtest\n' > tcw-config.yaml
   tcw init work
   cat > docs/work/inbox/2026-08-19-another-raw-request.md <<'MD'
   # Another Raw Request

   Body.
   MD
   tcw work inbox accept 2026-08-19-another-raw-request
   tcw work list
   ```

   Expected, and this is the item's whole reason for existing:
   `→ now at docs/work/backlog/2026-08-19-another-raw-request` and a `tcw work
   list` row whose title is `Another Raw Request`. Today this prints
   `2026-08-19-2026-08-19-another-raw-request` twice over.

   Note the editable install pins to the primary checkout — if this item is
   implemented on a worktree branch, re-point it before trusting this run.

2. **The delegate/escalate round trip, across two real nodes.** The suite tests
   `_inbox_write`'s output shape and `inbox_accept`'s input handling separately;
   nothing joins them end to end, and the cross-node epic path is the reason
   this bug mattered. Create a parent node and a registered child, then:

   ```sh
   echo "details" | tcw work delegate <child-id> "Ship the exporter"
   # in the child node:
   tcw work inbox list          # shows <today>-ship-the-exporter.md
   tcw work inbox accept <today>-ship-the-exporter
   tcw work list                # title must be "Ship the exporter"
   ```

   The title must round-trip to the string passed to `delegate`, and the slug
   must carry one date. Repeat with `tcw work escalate` from the child.

3. **`tcw work new` on the two crashing inputs, through the binary.** Task 1's
   tests call `main()` in-process; confirm the packaged entry point also exits
   `0` rather than printing a traceback:

   ```sh
   tcw work new "東京"; echo "exit=$?"
   tcw work new "$(python3 -c 'print("a"*300)')"; echo "exit=$?"
   ```

   Both must print a slug and exit `0`.

4. **Read the two capability descriptions as a user would.** `tcw capabilities
   show work/manage-the-work-inbox` and `work/open-a-work-item` — the added
   sentences have to read as product statements, not as changelog entries.

---

## Notes

**On the `OSError` and the sibling item.** `2026-07-30-fix-non-git-write-paths-…`
adds a generic handler to `main()` that catches **`subprocess.CalledProcessError`
only** (its spec, `## Design`, shows the exact `except` clause). It does not
catch `OSError`, so the `[Errno 63] File name too long` this item found escaping
`_ERRORS` (`tcw/work/cli.py:41`) is **entirely this item's**, and none of it is
absorbed by that item's CLI-boundary work.

That is also the right split rather than an accident of ordering. Catching
`OSError` in `main()` would turn a crash into a clean error message, but the
command would still fail — the user's title would remain unusable. Bounding the
slug (Task 1) makes the command *succeed*, which is what they wanted. If a
future item does add an `OSError` handler for genuinely unwritable paths (a
read-only filesystem, a permission denial), it complements Task 1 rather than
replacing it.

**Ordering against the batch.** This item implements last of four. The other
three concentrate on `FsTreeStore`, `FsTaxonomyStore` and `FsCapabilitiesStore`;
this one touches `FsWorkStore` plus two small additions to `tcw/store/base.py`.
The single real overlap is `2026-07-30-fix-non-git-write-paths-…`, which adds
`self._require_repository()` as the first line of ~18 public write methods
**including `FsWorkStore.inbox_accept`**. That lands *before* this item and does
not touch the title or slug lines this plan edits, so the two are compatible —
but it is why every method here is named by symbol. Expect all `tcw/store/fs.py`
line numbers in this plan and in `spec.md` to be stale by the time this is
implemented; re-locate by symbol, and treat a line number that does not resolve
as drift rather than as a contradiction.

`_require_repository` on `inbox_accept` also means the new inbox tests must run
inside a git repository. The existing `node()` helper (`tests/test_work.py:15`)
already runs `git init`, so no test needs changing for it.

**No blockers recorded.** `tcw work edit --blocked-by` would be right if this
item could not start until the sibling landed, but it can: nothing here reads or
calls `require_repository`, and the overlap is a different line of the same
method. The ordering is a batch-sequencing preference, not a dependency.

**What was deliberately not planned.** No new CLI flag, no config knob for the
precedence, no pluggable title extractor, and no change to `slugify`'s ASCII-only
behavior — the spec's Non-goals cover each, and the `unicodedata.normalize`
upgrade for accented titles is noted there as its own future item.
