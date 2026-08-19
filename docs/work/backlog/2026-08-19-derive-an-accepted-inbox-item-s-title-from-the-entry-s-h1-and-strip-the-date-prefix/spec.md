# Spec — Derive an accepted inbox item's title from the entry's H1 and strip the date prefix

## Capability changes

**Changed — one capability, no status change.**

`work/manage-the-work-inbox` (`docs/capabilities/work/manage-the-work-inbox/`,
`id: cap-e3d385`, Status `Supported`, Feature `work-inbox`). Its
`description.md` describes what accepting an entry *produces* — the item, the
attachments, the `intake.md` — but never says where the item's **title** comes
from, so the defect below was never contradicted by the ledger. The description
gains a sentence naming the derivation precedence. Status stays `Supported`.

**No taxonomy delta.** `tcw taxonomy list` already registers the Feature
`work-inbox` ("the intake surface through which users inspect and accept raw
requests as formal work items") and the Vocabulary `work-item/intake`. This
change refines how an existing Feature behaves; it introduces no new term and
retires none.

**No new capability, none removed.** `work/capture-raw-intake`,
`work/delegate-a-request-to-a-child-node` and
`work/escalate-a-request-to-the-parent-node` are unaffected — see the sweep in
`## Problem`.

## Reproduction

Verified against `tcw 1.0.0` (the working tree) on 2026-08-19, in a scratch node
outside this repo.

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

Observed:

```
→ now at docs/work/backlog/2026-08-19-2026-08-19-another-raw-request
2026-08-19-2026-08-19-another-raw-request
2026-08-19-2026-08-19-another-raw-request | backlog | i | - | 2026-08-19-another-raw-request
```

Expected: slug `2026-08-19-another-raw-request`, title `Another Raw Request`.

All three entry shapes were checked in the same scratch node, and all three
carry the defect:

| entry | title produced | slug produced |
| --- | --- | --- |
| `2026-08-19-another-raw-request.md`, H1 `# Another Raw Request` | `2026-08-19-another-raw-request` | `2026-08-19-2026-08-19-another-raw-request` |
| folder `2026-08-19-folder-request/` with `INDEX.md` (frontmatter + H1) | `2026-08-19-folder-request` | `2026-08-19-2026-08-19-folder-request` |
| `2026-08-19-no-heading.md`, no H1 at all | `2026-08-19-no-heading` | `2026-08-19-2026-08-19-no-heading` |

`--title` is unaffected: `tcw work inbox accept <entry> --title "Clean Title"`
produces slug `2026-08-19-clean-title` and title `Clean Title`.

## Problem

### Root cause

`FsWorkStore.inbox_accept` uses the entry's *presentation label* as the work
item's title:

- `tcw/store/fs.py:3002` — `accepted_title = (title or detail.entry.title).strip()`
- `tcw/store/fs.py:2940` — `entry = InboxEntry(ref=ref, title=path.stem if path.is_file() else path.name, ...)`
  (`inbox_list` builds the same label at `tcw/store/fs.py:2969`)

So with no `--title`, the item's title is the file stem (or, for a folder entry,
the folder name) verbatim — date prefix included. That label is then re-dated
into the slug:

- `tcw/store/fs.py:3005` — `created = date.today().isoformat()`
- `tcw/store/fs.py:3006` — `slug = self._unique_slug(created, accepted_title)`
- `tcw/store/fs.py:2441-2445` — `_unique_slug` builds `f"{created}-{slugify(title)}"`
- `tcw/store/fs.py:640-641` — `slugify` lowercases and hyphenates; it has no
  notion of a date prefix, so `2026-08-19-another-raw-request` survives intact

The title is also written straight into state at `tcw/store/fs.py:3038`
(`state = {"slug": slug, "title": accepted_title, ...}`), which is what
`tcw work list` renders.

The entry's `# ` heading is never read. `FsWorkStore._frontmatter`
(`tcw/store/fs.py:2296`) is the only body parsing `inbox_accept` does, and it is
called solely to lift the `initiative` back-pointer
(`_inbox_initiative`, `tcw/store/fs.py:2978-2993`).

### Why the cross-node epic path always hits it

`_inbox_write` (`tcw/work/recursion.py:257-276`), the single writer behind both
`tcw work delegate` and `tcw work escalate` (`tcw/work/recursion.py:279`, `:292`),
names its entry `f"{date.today().isoformat()}-{slugify(title)}"`
(`tcw/work/recursion.py:268`) and writes the body as
`"---\n" + front + "\n---\n\n" + f"# {title}\n\n{body}\n"`
(`tcw/work/recursion.py:274-276`).

Every delegated/escalated entry therefore arrives with (a) a date-prefixed
filename and (b) an authoritative `# Title` H1 that is **not on the first line**
— it sits after the `from:`/`initiative:` frontmatter block. `inbox_accept`
ignores (b) and consumes (a).

TCW ships its own workaround for this:
`skills/tcw-work/references/stage-inbox.md:42` instructs agents to run
`tcw work inbox accept <entry> --title "<clear title>"`, i.e. never to rely on
the derived title. The reporter carries the same standing workaround in their
workspace's `AGENTS.md`.

### Repo-wide sweep for sibling defects

The sweep covered every place in `tcw/` that derives a name from a filename, and
every place a date prefix is applied. `grep -rn "entry.title\|\.stem\|slugify("
tcw/ --include=*.py` returns exactly the sites below; there are no others.

| site | derives from | verdict |
| --- | --- | --- |
| `tcw/store/fs.py:3002` | inbox entry filename → item title | **the defect** |
| `tcw/store/fs.py:2940`, `:2969` | inbox entry filename → `InboxEntry.title` | **correct as-is, do not change.** This label is the entry's addressable identifier: `_resolve_inbox_ref` step 3 resolves an entry by its listed title (`tcw/store/fs.py:2894`), and `tests/test_work.py:275` pins that. Making it the H1 would move ambiguity from filenames (unique by construction) to headings (not unique) and break addressing by stem. |
| `tcw/work/recursion.py:268` | title → dated entry filename | correct: it prefixes a date to a slug that has none. The inverse of the defect, and the reason the H1 is authoritative. |
| `tcw/store/fs.py:3311` (`create_work`, behind `tcw work new`) | caller-supplied title → dated slug | correct: the title is a required positional argument the user typed. `tcw work new "2026-08-19-foo"` would double-date, but that is the user's own string, not a TCW naming convention leaking. Non-goal. |
| `tcw/store/fs.py:1009` (`FsTaxonomyStore.add`) | term name → slug, no date involved | not affected |
| `tcw/store/fs.py:2802` | `path.stem` compared against declared plan stages | not a title/slug derivation |

**`tcw work scaffold`**: derives nothing from a filename. `_scaffold`
(`tcw/work/cli.py:830-897`) takes an explicit artifact name and an item slug.
Not affected.

**The `serve` HTTP surface**: has **no** inbox surface at all —
`grep -rn "inbox_accept\|inbox_list\|inbox_show" tcw/` returns hits only in
`tcw/work/cli.py`, `tcw/store/fs.py` and `tcw/store/base.py`. `tcw/serve/` never
reaches the inbox, so it cannot carry a sibling of this defect. This is the only
narrowing in the sweep, and it is a narrowing by absence rather than by choice.

**Harness parity**: there is no built-in `inbox` stage prompt —
`load_builtins` derives its stage set as `set(STAGE_IDS) - {"inbox"}`
(`tcw/work/resolve.py:65`), so `skills/tcw-work/references/stage-inbox.md` is the
sole home of the `--title` guidance and both harnesses read the same file. No
Claude-only or Codex-only path exists here. The fix itself lands in the `tcw`
CLI, which behaves identically under both.

### Documentation that asserts the current (wrong) behavior

- `README.md:930` — "the command does not require or parse that template".
  Becomes half-untrue: the command will parse the template's H1.
- `docs/work-inbox-template.md:1` — the template's own placeholder heading is
  literally `# Request title`, and line 20 repeats "TCW does not parse or
  require its sections".
- `skills/tcw-work/references/stage-inbox.md:42` — the mandatory `--title`
  workaround.
- `skills/tcw-work/references/commands.md:6` — already writes `--title` as
  optional (`[--title <t>]`); accurate either way.

## Goals

1. `tcw work inbox accept <entry>` with no `--title` gives the item the title the
   entry's own `# ` H1 declares, when it has one.
2. When there is no usable H1, the filename fallback no longer carries TCW's
   `YYYY-MM-DD-` naming prefix into a human-facing title, and therefore no
   longer re-dates it into the slug.
3. The reporter's reproduction produces slug `2026-08-19-another-raw-request`
   and title `Another Raw Request`, with no `--title`.
4. Entries written by `tcw work delegate` / `tcw work escalate` — frontmatter
   first, H1 second — resolve to their H1.
5. The `--title` override, and every other observable behavior of
   `inbox accept` (atomicity, attachments, `intake.md` contents, `initiative`
   handling, entry consumption), is unchanged.

## Non-goals

- **Changing `InboxEntry.title`**, or what `tcw work inbox list` /
  `tcw work inbox show` print. See the sweep table: that label is the entry's
  addressable identifier. A consequence is a visible mismatch — `list` shows
  `2026-08-19-another-raw-request` while `accept` produces
  `Another Raw Request` — which is accepted here and noted in `## Risks`.
- **Reusing the entry's dated filename stem as the item's slug.** The issue's
  expected slug (`2026-08-19-another-raw-request`) falls out of the existing
  `<accept-date>-<slugified-title>` rule once the title is right — no slug rule
  changes. Reusing the stem would desynchronize the slug's date from
  `state.yaml: created` (`tcw/store/fs.py:3005`, `:3038`) whenever an entry is
  accepted on a day after it was filed, and would bypass `_unique_slug`'s
  collision suffix. Verified: `_unique_slug("2026-08-19", "Another Raw Request")`
  → `2026-08-19-another-raw-request`.
- **Stripping a date prefix from an H1-derived or `--title`-supplied title.**
  Those are human-authored strings; a heading is not TCW's naming convention.
- **Full CommonMark heading support** — setext headings (`Title` / `=====`),
  indented ATX headings, ATX closing sequences (`# Title #`), inline emphasis
  stripping. Out of scope; the fallback covers what these miss.
- Any change to `tcw work new`, `delegate`, `escalate`, `scaffold`, or the
  `serve` surface.
- The reporter's side note about `pip show tcw` reporting stale metadata
  (`0.10.3`) while `tcw --version` reports `1.0.0`. Unrelated to this defect;
  it is an install-metadata problem, not a TCW behavior.

## Design

### Precedence

The accepted title is the first of these that yields a non-empty string:

1. **Explicit `--title`** (`tcw/work/cli.py:1329` → `:292` → `inbox_accept`'s
   `title` parameter). Used verbatim, stripped of surrounding whitespace, with
   no H1 scan and no date stripping.
2. **The first ATX H1 in the entry's primary body** (`InboxEntryDetail.body`).
3. **`InboxEntry.title`** — the file stem or folder name — with a leading
   `YYYY-MM-DD-` removed.

The existing empty-title guard (`tcw/store/fs.py:3003-3004`) stays as the floor.

### Rule 2, pinned

Scanning `InboxEntryDetail.body`, in order:

- **Frontmatter is skipped.** If the body's first line is exactly `---`, scanning
  starts after the next line that is exactly `---`. This is what makes the
  delegate/escalate shape work (`tcw/work/recursion.py:274-276`).
- **Fenced code blocks are skipped.** A line whose stripped form opens with
  ```` ``` ```` or `~~~` toggles a fence; lines inside a fence are not
  candidates. Without this, a shell comment (`# tcw version: ...`) inside a
  ```` ```sh ```` block in a pasted bug report becomes the item's title — a shape
  this very item's `intake.md` demonstrates.
- **A candidate is a line that starts at column 0 with `#` followed by a space.**
  `##` is not an H1. Indented headings are not candidates.
- **The title is the rest of the line, stripped.** If that is empty (`#`, `# `,
  `#   `), the line is not a match and scanning continues.
- **The body is format-agnostic**: a folder entry's `INDEX.txt` is scanned by the
  same rule as an `INDEX.md`. One code path; a plain-text file opening with
  `# Foo` overwhelmingly means it as a title.
- **`body is None`** (a binary primary resource, e.g.
  `tests/test_work.py:229`) yields no candidate and falls through to rule 3.

### Rule 3, pinned

- The prefix removed is exactly `^\d{4}-\d{2}-\d{2}-` — shape, not calendar
  validity. `2026-13-45-foo` strips; a stricter date check buys nothing, since
  the shape is TCW's own convention.
- The trailing hyphen is part of the pattern, so a file named `2026-08-19.md`
  keeps the title `2026-08-19`.
- If stripping would leave an empty string (a file literally named
  `2026-08-19-.md`), the **unstripped** label is kept. Erroring on an entry that
  does have a name would be worse than an odd title the user can override.

### Interaction with `--title ""`

Unchanged. `--title ""` is falsy at `tcw/store/fs.py:3002` today and falls
through to derivation; it continues to, now landing on the H1 instead of the
filename. Turning it into an error is a separate decision and is not made here.

### Where the logic belongs

Two pieces, two different homes.

- **"An accepted item's title comes from the entry's body when the body declares
  one"** is a *store-interface* rule. Any store can honor it: it reads
  `InboxEntryDetail.body`, which the abstract interface already exposes
  (`tcw/store/base.py:1330-1335`), and a Jira- or wiki-backed adapter has a body
  with a heading just as a file does. The rule is documented on the abstract
  `inbox_accept` (`tcw/store/base.py:1545-1546`), and the heading scan itself —
  a pure string→`str | None` function — is shared, not `FsWorkStore`-private, so
  a second adapter inherits it rather than reinventing it.
- **Stripping `YYYY-MM-DD-` from the filename fallback** is a *filesystem-adapter
  private detail*. The prefix is a convention `_inbox_write` invents for
  filenames (`tcw/work/recursion.py:268`); a non-filesystem store has no
  filename and no prefix to strip. It stays inside `FsWorkStore`.

Nothing here reconstructs state from git, globs an open namespace, hard-codes a
path, or reads directory ancestry.

### Deliberately not done

No new CLI flag, no configuration knob for the precedence, no pluggable title
extractor. The rule is fixed, `--title` is already the escape hatch, and one
override is enough.

## Abstraction litmus test

| operation | verdict |
| --- | --- |
| `inbox_accept(ref, title=None)` — existing abstract operation (`tcw/store/base.py:1545`). Its **contract** gains a documented title-derivation precedence; its signature does not change. | **Model / store interface.** "Prefer the title the entry's body declares" is expressible against `InboxEntryDetail.body`, which the abstract interface already provides. A non-filesystem store can implement it — a Jira issue's summary field or a wiki page's first heading is the same read, less elegantly. |
| Extracting the first ATX H1 from a body string. | **Model-adjacent, shared.** A pure function over `body`, with no filesystem dependency. Lives beside the store contract, not inside the FS adapter, so a second adapter reuses it. |
| Stripping a leading `YYYY-MM-DD-` from `InboxEntry.title` before using it as a fallback. | **Filesystem-adapter private detail.** The prefix exists only because `_inbox_write` puts it in a *filename*. There is no abstract analog — an abstract store's entry label carries no TCW date convention — so it stays private to `FsWorkStore`. |
| Slug construction (`_unique_slug`, `tcw/store/fs.py:2441`). | **No change.** Named here because a reader may expect one: the issue's expected slug is produced by the existing rule once the title is corrected. |

No new abstract operation is added.

## Acceptance criteria

Each is checkable by running the named command against a fresh node. Criteria
1-4 correspond to shapes reproduced above; 9-12 are executable against the tree
today and were run while writing this spec.

1. In a fresh node, an inbox entry `2026-08-19-another-raw-request.md` whose
   first line is `# Another Raw Request`, accepted with
   `tcw work inbox accept 2026-08-19-another-raw-request` (no `--title`),
   produces an item whose `state.yaml` has `title: Another Raw Request` and
   `slug: 2026-08-19-another-raw-request`, and whose folder is
   `docs/work/backlog/2026-08-19-another-raw-request/`.
2. An entry written by `_inbox_write` — `---\nfrom: parent\n---\n\n# Do the thing\n\ndetails\n` —
   accepted with no `--title`, produces title `Do the thing` (not `req`, not the
   dated stem). The H1 is found although it is line 5, not line 1.
3. A folder entry `2026-08-19-folder-request/` whose `INDEX.md` declares
   `# Folder Request Title` produces title `Folder Request Title`. The same
   entry with `INDEX.txt` instead of `INDEX.md` produces the same title.
4. An entry `2026-08-19-no-heading.md` containing no `# ` heading produces title
   `no-heading` and slug `<today>-no-heading` — one date, not two.
5. An entry whose only `# `-prefixed line sits inside a ```` ```sh ```` fence
   falls through to the filename fallback; the shell comment does not become the
   title.
6. An entry whose body begins `## Sub` and later contains `# Real` produces
   title `Real`: `##` is not an H1.
7. An entry whose body contains `#`, then `#   `, then `# Real` produces title
   `Real`: a heading with no text is not a match.
8. `tcw work inbox accept <entry> --title "Clean Title"` produces title
   `Clean Title` and slug `<today>-clean-title` for every entry shape above,
   including one with a competing H1 — the override wins and no H1 is read.
9. `tcw work inbox list` output is byte-identical before and after the change
   for the entries above: `2026-08-19-another-raw-request.md | file | 2026-08-19-another-raw-request`.
   `InboxEntry.title` is unchanged. (Run: current output confirmed.)
10. `python -m pytest tests/test_work.py -k inbox` passes with no test modified
    to accommodate the change. (Run: `21 passed, 161 deselected` on the tree
    today; every one of those tests either supplies an explicit `title=` or uses
    a body with no H1, except the four `_delegated` tests at
    `tests/test_work.py:341-390`, which assert only `initiative`, `intake.md`
    contents and non-consumption — never the slug or title literal.)
11. `python -m pytest` passes in full. (Baseline run while writing this spec:
    `1763 passed in 298.70s`. Any failure after the change is caused by it.)
12. An entry named `2026-08-19.md` (no trailing hyphen) with no H1 produces
    title `2026-08-19`; an entry named `2026-08-19-.md` with no H1 produces
    title `2026-08-19-`. Neither raises "title is required and must be
    non-empty".
13. A binary entry (`sample.dat`, no readable body) accepted with no `--title`
    produces title `sample` — the stem, undated because the name is undated —
    and does not raise. (`tests/test_work.py:229` covers the surrounding
    behavior.)
14. `skills/tcw-work/references/stage-inbox.md` step 5 no longer instructs
    `--title` as mandatory, and `README.md:930` /
    `docs/work-inbox-template.md` no longer claim the command never parses the
    template, since it now reads the template's `# ` heading.
15. `docs/capabilities/work/manage-the-work-inbox/description.md` states the
    three-step precedence, and `tcw validate` still reports `validate OK`
   (baseline run while writing this spec).
16. `docs/changelogs/upcoming.md` (Fixed) and
    `docs/release-notes/upcoming.md` carry an entry for this change.

## Risks

- **A latent H1 changes an established title silently.** Anyone who has been
  accepting entries bare and living with slug-shaped titles gets different
  titles after upgrading. This is the fix, not a regression, but it is a
  behavior change on a command with no deprecation path. Mitigated by `--title`,
  which is unchanged, and by the release note.
- **`docs/work-inbox-template.md` opens with the literal placeholder
  `# Request title`.** A user who copies the template and edits the body without
  editing the heading now gets an item titled "Request title" instead of a
  slug-shaped one. Arguably still an improvement — it is at least prose — but
  the template should tell them to replace it. Folded into criterion 14.
- **The heading scan is a heuristic, not a Markdown parser.** Deliberate (see
  Non-goals). The known misses are setext headings, indented headings, and
  `# ` lines inside HTML blocks or blockquote-indented content. Every miss falls
  back to the filename, which is the current behavior minus the date prefix —
  so the worst case is no worse than today.
- **Fence tracking is line-prefix based**, so a fence opened inside a list item
  with indentation, or an unclosed fence, mis-scopes. An unclosed fence
  suppresses every heading after it and falls back to the filename; that is the
  safe direction.
- **`2026-08-19-.md` with no H1** still yields the doubled-date slug
  `2026-08-19-2026-08-19`, because the fallback keeps the unstripped label
  rather than erroring. Pathological filename; `--title` covers it.
- **Test-suite risk is low but not zero.** Criterion 10 is the guard: if any
  existing test needs editing to pass, the derivation is doing something the
  spec did not intend, and that is a signal to stop rather than to edit the
  test.

## Notes

**Prototype.** The precedence and every pinned edge case above were implemented
as a standalone ~25-line function and run against 15 assertions covering all of
them (frontmatter, fences, `##`, empty headings, `body is None`, the degenerate
filenames, `--title ""`, and a title ending in `#`). All passed. The prototype
lives in the session scratchpad, not in the repo — it is evidence the rule is
coherent, not the implementation.

**On the "reuse the dated stem as the slug" reading.** The issue's *Remediation*
paragraph can be read as asking for the entry's filename stem to become the
slug. It does not need to be: correcting the title alone yields exactly the slug
the issue's *Expected* section names, because the accept date and the entry's
filed date coincide in the reproduction. Where they do not coincide — an entry
filed on the 1st and accepted on the 19th — the two readings diverge, and this
spec takes the smaller one (`## Non-goals`). If the reporter meant the slug must
preserve the *filing* date rather than the *acceptance* date, that is a
different change to `_unique_slug` and `state.yaml: created`, and it should be
its own item.

**Open question, not blocking.** With `InboxEntry.title` deliberately unchanged,
`tcw work inbox list` shows one string and `accept` produces another. A single
`accepts as: <derived title>` line in `tcw work inbox show`'s output would close
that gap for one line of code, but it changes a documented CLI surface
(`tests/test_documented_cli_surface.py`) and the capability description. Left
out of this item on purpose; worth filing separately if the mismatch confuses
anyone in practice.
