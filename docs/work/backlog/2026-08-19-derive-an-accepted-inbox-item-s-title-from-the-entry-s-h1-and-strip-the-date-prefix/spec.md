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

`_inbox_write` (`tcw/work/recursion.py:258-276`), the single writer behind both
`tcw work delegate` and `tcw work escalate` (which call it at
`tcw/work/recursion.py:288` and `:299`), names its entry
`f"{date.today().isoformat()}-{slugify(title)}"` (`tcw/work/recursion.py:268`)
and writes the body as
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
| `tcw/store/fs.py:3311` (`create_work`, behind `tcw work new`) | caller-supplied title → dated slug | **date handling correct; slug construction shares the defect found below.** `tcw work new "2026-08-19-foo"` would double-date, but that is the user's own string, not a TCW naming convention leaking — non-goal. It does, however, route through the same `_unique_slug`, and therefore carries the unbounded-slug crash described in *Sibling defect: `_unique_slug` does not bound its output*. |
| `tcw/store/fs.py:1009` (`FsTaxonomyStore.add`) | term name → slug, no date involved | not affected |
| `tcw/store/fs.py:2802` | `path.stem` compared against declared plan stages | not a title/slug derivation |
| `tcw work edit --title` (`tcw/store/fs.py:3455`) | new title → **no re-slug** | not affected, and correct: `docs/capabilities/work/retitle-a-work-item/description.md:2` states the slug is the stable ID and does not change on retitle. Retitling therefore cannot reach the slug hazards below. |

#### Sibling defect: `_unique_slug` does not bound its output

Found by the sweep, not by the report, and **in scope** because this change is
what makes it easy to reach. `_unique_slug` (`tcw/store/fs.py:2441-2445`) builds
`f"{created}-{slugify(title)}"` and loops only on collisions with existing
items. It never checks that `slugify(title)` is non-empty or of bounded length.
Today the inbox path always feeds it a filename stem, which is already
slug-shaped and bounded by the filesystem's own 255-byte component limit, so the
hazard is nearly unreachable there. `create_work` has no such protection, and
after this change neither does the inbox path — an H1 is prose.

Both failures reproduce today, in the scratch node, through `tcw work new`:

```
$ tcw work new "東京"
→ created at docs/work/backlog/2026-08-19-      # trailing-hyphen slug
$ tcw work new "東京"
→ created at docs/work/backlog/2026-08-19--2    # and it collides with itself
$ tcw work new "$(python3 -c 'print("a"*300)')"
OSError: [Errno 63] File name too long: '.../backlog/2026-08-19-aaaa…'
```

The `OSError` escapes as a traceback because `_ERRORS` (`tcw/work/cli.py:41`)
lists `ValueError, IllegalTransition, MultipleMatch, TransitionCommitError,
AlreadyClaimed` — not `OSError`. On the inbox path the same crash lands one line
earlier, at `tempfile.mkdtemp(prefix=f".{slug}-", ...)` (`tcw/store/fs.py:3036`),
whose prefix makes the component ten characters longer than the slug itself.

The fix belongs in `_unique_slug`, the single choke point both callers share —
one guard there is a smaller diff than a guard in each caller, and guarding only
the inbox path would leave `tcw work new` still crashing. See `## Design`.

**`tcw work scaffold`**: derives nothing from a filename. `_scaffold`
(`tcw/work/cli.py:830-897`) takes an explicit artifact name and an item slug.
Not affected.

**The `serve` HTTP surface**: has **no** inbox surface at all. The evidence is
not a grep for three method names — that would only prove the server does not
call *those*, leaving a differently-implemented inbox route possible. The string
`inbox`, case-insensitively, appears **zero** times anywhere under `tcw/serve/`:
not in `runtime.py` or `__init__.py`, not in the bundled server
(`tcw/serve/dist/server.cjs`), and not in the client bundle
(`dist/client/index.html`, `theme-init.js`, `assets/*.js`, `assets/*.css`).
There is no inbox route, no inbox view, and no inbox label to render. `serve`
therefore cannot carry a sibling of this defect. This is the only narrowing in
the sweep, and it is a narrowing by absence rather than by choice.

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
4. For entries written by `tcw work delegate` / `tcw work escalate` — frontmatter
   first, H1 second — the derived title is the text of that H1 line. This is
   *not* a guarantee that the title round-trips back to the string passed to
   `delegate`: see `## Non-goals` for the two cases where it does not.
5. No title, from any source, can produce an empty, degenerate, or
   filesystem-rejected slug. `tcw work inbox accept` and `tcw work new` both
   stop crashing on a title that slugifies to nothing or is very long.
6. The `--title` override, and every other observable behavior of
   `inbox accept` (atomicity, attachments, `intake.md` contents, `initiative`
   handling, entry consumption), is unchanged.

## Non-goals

- **Changing `InboxEntry.title`**, or what `tcw work inbox list` /
  `tcw work inbox show` print. See the sweep table: that label is the entry's
  addressable identifier. A consequence is a visible mismatch — `list` shows
  `2026-08-19-another-raw-request` while `accept` produces
  `Another Raw Request` — which is accepted here and noted in `## Risks`.
- **Reusing the entry's dated filename stem as the item's slug.** The slug keeps
  its existing rule: `<acceptance-date>-<slugified-title>`. Stated precisely,
  because the earlier draft overclaimed here: the issue's expected slug
  `2026-08-19-another-raw-request` falls out of that rule **only because the
  reporter filed and accepted on the same day, with no colliding item**. An entry
  filed on the 1st and accepted on the 19th becomes `2026-08-19-…`, not
  `2026-08-01-…`, and that is intended. Reusing the stem would desynchronize the
  slug's date from `state.yaml: created` (`tcw/store/fs.py:3005`, `:3038`) and
  would bypass `_unique_slug`'s collision suffix. Both divergent cases are
  pinned as acceptance criteria rather than left implied.
- **Stripping a date prefix from an H1-derived or `--title`-supplied title.**
  Those are human-authored strings; a heading is not TCW's naming convention.
- **Full CommonMark heading support** — setext headings (`Title` / `=====`),
  indented ATX headings, ATX closing sequences (`# Title #`), inline emphasis
  stripping. Out of scope; the fallback covers what these miss. Two consequences
  are accepted rather than fixed, and both are pinned as criteria:
  `tcw work delegate "Fix auth #"` yields the title `Fix auth #`, and a delegated
  title containing a newline (`_inbox_write` interpolates it into `# {title}`
  unvalidated, `tcw/work/recursion.py:274-276`) yields only its first line. Both
  are still strictly better than today's dated-slug title.
- **Teaching `slugify` about non-ASCII.** `slugify` (`tcw/store/fs.py:640-641`)
  keeps only `[a-z0-9]`, so `Café déjà vu` → `caf-d-j-vu` and `C++ / C#` → `c-c`
  (distinct headings can collide, which `_unique_slug` then resolves with `-2`).
  This is an **inherited limitation, declared not fixed**: the slug is an
  identifier, the title itself stays correct, and `slugify` is shared with the
  taxonomy and capability axes, so changing it would re-slug far more than this
  item. A one-line stdlib upgrade exists —
  `unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()` before
  the substitution, giving `cafe-deja-vu` — and is worth its own item. What is
  *not* left inherited is the crashing and degenerate cases; see `## Design`.
- Any change to `delegate`, `escalate`, `scaffold`, or the `serve` surface.
  `tcw work new` is touched only through the shared `_unique_slug` guard
  (Goal 5); its title handling, arguments, and output are otherwise unchanged.
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

- **Frontmatter is skipped, by exactly the same boundary rule `_frontmatter`
  already uses** (`tcw/store/fs.py:2296-2310`), not a second parser: the body
  qualifies only if it `startswith("---\n")`, and the block ends at the first
  `"\n---\n"` found from offset 4; scanning starts five characters after that.
  If either test fails, the whole body is scanned from the top. This is what
  makes the delegate/escalate shape work (`tcw/work/recursion.py:274-276`), and
  the parity is load-bearing rather than cosmetic — two definitions of "leading
  frontmatter" would drift. The implementation must share one boundary
  computation with `_frontmatter`, not restate it.

  Parity means these four cases are *decided*, not accidental. All four were
  checked against `FsWorkStore._frontmatter` directly:

  | body shape | `_frontmatter` | title scan |
  | --- | --- | --- |
  | CRLF (`---\r\n…`) | not frontmatter (no `---\n` prefix), returns `None` | whole body scanned; `from: parent` is not an H1, so the real H1 still wins |
  | UTF-8 BOM before `---` | not frontmatter, returns `None` | same — H1 still wins |
  | opening `---` never closed (EOF) | **raises** `malformed YAML frontmatter` | unreachable: `_inbox_initiative` runs at `tcw/store/fs.py:3001`, one line *before* title derivation, so acceptance already failed |
  | leading thematic-break `---`, an H1, then another `---` | parses `\n# Swallowed\n` as YAML → all comment → returns `None` | that first H1 is **skipped**; the entry falls back to a later H1 or to the filename |

  The last row is a real, accepted miss — documented in `## Risks`, not fixed. A
  Markdown body that opens with a horizontal rule is rare, and distinguishing it
  from frontmatter is exactly the ambiguity CommonMark itself has.
- **Fenced code blocks are skipped**, matching on the delimiter's **character
  and run length**, not on a bare toggle. An unfenced line matching
  `^(`{3,}|~{3,})` after stripping opens a fence and the match is remembered; a
  fence closes only on a line whose delimiter is the *same character* with a run
  *at least as long*. Without the fence skip at all, a shell comment
  (`# tcw version: ...`) inside a ```` ```sh ```` block in a pasted bug report
  becomes the item's title — a shape this very item's `intake.md` demonstrates.
  Without the run-length rule, this valid Markdown selects the wrong heading:

  ~~~markdown
  ````
  # Example inside documentation
  ```
  # Still inside the four-backtick fence
  ````

  # Real request title
  ~~~

  A bare toggle closes at the inner three-backtick line and returns
  `Still inside the four-backtick fence`. The char-and-length rule returns
  `Real request title`. Both outcomes were run against a prototype. (A `~~~`
  line inside a backtick fence is *already* handled by remembering the opening
  delimiter, and was never the problem; the run length is.)
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

### Slug safety for a derived title

Feeding `slugify` a human-written heading is new. Until now the inbox path fed
it a filename stem — already `[a-z0-9-]`-shaped and already bounded by the
filesystem — so `_unique_slug` had nothing to mangle. Two of the resulting
hazards are fixed here; the third is declared inherited in `## Non-goals`.

**1. Empty slug body — fixed at the shared choke point.** `_unique_slug`
(`tcw/store/fs.py:2441-2445`) uses `slugify(title) or "untitled"` in place of
`slugify(title)`. `# 東京` then yields title `東京` and slug
`2026-08-19-untitled`; a second such item collides and the *existing* loop makes
it `2026-08-19-untitled-2`. No new collision logic.

Why here and not in `inbox_accept`: `tcw work new "東京"` produces the
trailing-hyphen slug `2026-08-19-` **today** (reproduced above). One guard in the
function both callers share fixes both; a guard in the inbox path alone leaves
`tcw work new` broken. This is the same reason the sweep pulled `_unique_slug`
into scope.

**Additionally, inbox-side:** when the derived title slugifies to empty but the
entry's date-stripped label does not, `inbox_accept` passes that label as the
slug source while keeping the H1 as the *title*. So `# 東京` in
`2026-08-19-tokyo-request.md` gives title `東京` and the readable slug
`2026-08-19-tokyo-request` rather than `2026-08-19-untitled`. This is one
conditional at the call site, it cannot reach `create_work`, and `untitled`
remains the floor beneath it for when the label is non-ASCII too.

**2. Unbounded length — fixed at the same choke point.** `_unique_slug`
truncates the slugified body to **120 characters**, then `rstrip("-")` so a cut
never lands on a hyphen. The number is grounded, not round-guessed: the
filesystem component limit is 255 bytes; the slug adds an 11-character date
prefix; `tempfile.mkdtemp(prefix=f".{slug}-", ...)` (`tcw/store/fs.py:3036`) adds
ten more characters on the inbox path; `_unique_slug`'s collision suffix can add
a few. 120 leaves well over 100 characters of headroom, and it truncates nothing
real — the longest slug body in this repo's own `docs/work/` today is 97
characters. Two long titles sharing a 120-character prefix collide, and the
existing loop appends `-2`.

**3. Unicode and punctuation loss** (`Café déjà vu` → `caf-d-j-vu`, `C++ / C#` →
`c-c`) is **not** fixed — see `## Non-goals`. It mangles the identifier, never
the title, and it is reachable today through filenames and `tcw work new`.

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
| Slug **derivation rule** — `<acceptance-date>-<slugified-title>`. | **No change.** Named because a reader may expect one: the issue's expected slug is produced by the existing rule once the title is corrected. |
| Slug **safety floor** — `_unique_slug` (`tcw/store/fs.py:2441`) gaining an `or "untitled"` default and a 120-character cap. | **Filesystem-adapter private detail.** These bounds exist because a slug becomes a *directory name* subject to a 255-byte component limit and to `mkdtemp`'s prefix. An abstract store minting an ID has no such constraint, so nothing about this belongs in the interface. It stays inside `FsWorkStore`, where `_unique_slug` already lives as a private method. |
| Preferring the entry's date-stripped label as the *slug source* when the derived title slugifies to empty. | **Filesystem-adapter private detail**, for the same reason as the date-prefix strip above: it reads a filename-derived label that no abstract store has. |

No new abstract operation is added. The two slug changes are additions to an
existing private method, not to the store interface — which is the correct
verdict precisely because they are motivated by filesystem limits.

## Acceptance criteria

Criteria 1-23 are checkable by running the named command against a fresh node or
the test suite; 24-26 are documentation deliverables, verified by reading files,
and are grouped under their own heading. Where a criterion records a value
already observed on the tree today, it says so — those were run while writing
this spec.

### Title derivation

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
   including an entry whose body declares `# A Competing Heading` — the
   resulting title is `Clean Title`, never `A Competing Heading`.
9. `tcw work inbox list`, run on an inbox holding
   `2026-08-19-another-raw-request.md` (H1 `# Another Raw Request`), prints
   exactly `2026-08-19-another-raw-request.md | file | 2026-08-19-another-raw-request`.
   `InboxEntry.title` stays filename-derived even though the entry has an H1.
   (Run: this is the current output, and it must not change.)

### Delegate / escalate and slug construction

10. **Delayed acceptance.** An entry `2026-08-01-do-the-thing.md` written by
    `_inbox_write` (H1 `# Do the thing`), accepted on 2026-08-19, produces slug
    `2026-08-19-do-the-thing` and `state.yaml: created: '2026-08-19'`. The
    entry's own `2026-08-01` date does **not** survive into the slug, and the
    slug's date and `created` agree.
11. **Duplicate delegated requests.** Two `tcw work delegate` calls with the
    same title on the same day produce `<date>-do-it.md` and `<date>-do-it-2.md`
    (`_inbox_write`'s own collision loop, `tcw/work/recursion.py:269-271`), both
    carrying the identical H1 `# Do it`. Accepting both produces titles `Do it`
    and `Do it`, and slugs `<date>-do-it` and `<date>-do-it-2` — the second
    suffix coming from `_unique_slug`'s item-collision loop, not from the
    filename suffix, which acceptance ignores.
12. **Newline in a delegated title.** `tcw work delegate <child> "$(printf 'Fix
    auth\nurgently')"` writes `# Fix auth` / `urgently`; accepting it yields
    title `Fix auth`. This pins the accepted limitation, not a fix.
13. **ATX closing sequence.** An entry whose H1 is `# Fix auth #` yields the
    literal title `Fix auth #` and slug `<today>-fix-auth`.

### Slug safety

14. An entry whose H1 is `# 東京`, accepted with no `--title`, does not crash.
    In a file named `2026-08-19-tokyo-request.md` it produces title `東京` and
    slug `2026-08-19-tokyo-request`. In a file whose label also slugifies to
    empty, it produces title `東京` and slug `2026-08-19-untitled`; a second such
    entry produces `2026-08-19-untitled-2`.
15. An entry whose H1 is `# !!! ???` (punctuation only, slugifies to empty)
    behaves the same way as criterion 14 — no `<date>-` slug is ever created.
16. An entry whose H1 is 300 characters produces a slug whose final path
    component is at most 131 characters (`11` date + `120` cap) and does not
    raise `OSError`/`ENAMETOOLONG`. The title in `state.yaml` is the **full**
    300-character heading — only the slug is truncated.
17. `tcw work new "$(python3 -c 'print("a"*300)')"` and `tcw work new "東京"`
    both succeed and print a usable slug. (Both **fail today**:
    the first with an uncaught `OSError: [Errno 63] File name too long`, the
    second with the degenerate slug `2026-08-19-`. Verified in the scratch node.
    These are the regression tests for the sibling defect.)
18. `tcw work new` on a normal title is unchanged: `tcw work new "Another Raw
    Request"` still yields `2026-08-19-another-raw-request`.

### Existing behavior that must not move

19. An entry named `2026-08-19.md` (no trailing hyphen) with no H1 produces
    title `2026-08-19`; an entry named `2026-08-19-.md` with no H1 produces
    title `2026-08-19-`. Neither raises "title is required and must be
    non-empty".
20. A binary entry (`sample.dat`, no readable body) accepted with no `--title`
    produces title `sample` — the stem, undated because the name is undated —
    and does not raise. (`tests/test_work.py:229` covers the surrounding
    behavior.)
21. **The existing filename-fallback assertions remain valid.**
    `tests/test_work.py:286-287` accepts `example.md` with no `title=` and
    asserts the accepted title is exactly `"example"` — so the fallback *is*
    pinned by an existing test, and it must still pass, unchanged, because that
    body (`"do it\n"`) has no H1. Correcting an earlier draft of this spec,
    which implied nothing depended on filename derivation.
22. `python -m pytest tests/test_work.py -k inbox` passes. (Baseline on the tree
    today: `21 passed, 161 deselected`.) Of those, the delegated-entry tests
    (`_delegated` helper at `tests/test_work.py:337`, its callers through
    `:388`, one of them parameterized over three frontmatter shapes) assert only
    `initiative`, `intake.md` contents and non-consumption — never a slug or
    title literal — so the title they now derive (`Do the thing`) does not
    affect them.
23. `python -m pytest` passes. (Baseline on the tree today: `1763 passed`. A
    failure is a signal to investigate, not proof of causation — the count is
    recorded so the implementer can tell a new failure from a pre-existing one.)

### Documentation deliverables

Not fresh-node behavior; verified by reading the files.

24. `skills/tcw-work/references/stage-inbox.md` step 5 no longer instructs
    `--title` as mandatory, and `README.md:930` /
    `docs/work-inbox-template.md` no longer claim the command never parses the
    template, since it now reads the template's `# ` heading.
25. `docs/capabilities/work/manage-the-work-inbox/description.md` states the
    three-step title precedence and
    `docs/capabilities/work/open-a-work-item/description.md` reflects the slug
    floor; `tcw validate` exits `0`.
26. `docs/changelogs/upcoming.md` (Fixed) and
    `docs/release-notes/upcoming.md` carry an entry for this change, covering
    both the title derivation and the slug floor.

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
  with indentation, or an unclosed fence, mis-scopes. An earlier draft of this
  spec claimed fence errors "only fail in the safe direction" — **that was
  wrong**, and it is why the delimiter char and run length are now part of the
  rule (`## Design`): a bare toggle closes a four-backtick fence at an inner
  three-backtick line and *selects* a heading from inside a code block rather
  than merely suppressing one. With the corrected rule the residual misses are
  an unclosed fence (suppresses every later heading → falls back to the
  filename, genuinely the safe direction) and an indented fence opener (not
  recognized, so a heading inside it could still be selected). The latter is
  accepted: an inbox entry that indents a fenced block inside a list *and* puts
  a column-0 `# ` line inside it is not a shape worth a Markdown parser.
- **A leading thematic-break `---` swallows the first H1.** Pinned in
  `## Design`; the entry falls back to a later H1 or to the filename.
- **`2026-08-19-.md` with no H1** still yields the doubled-date slug
  `2026-08-19-2026-08-19`, because the fallback keeps the unstripped label
  rather than erroring. Pathological filename; `--title` covers it.
- **Slug truncation can collide.** Two titles sharing a 120-character slugified
  prefix produce the same base, and `_unique_slug`'s loop distinguishes them
  only with `-2`, `-3`. Acceptable: the slug is an opaque ID, the full title is
  in `state.yaml`, and this is already how same-titled items behave.
- **The `_unique_slug` guard is a wider blast radius than the reported bug.** It
  changes slug construction for `tcw work new` as well as the inbox. That is
  deliberate — the alternative leaves `tcw work new "東京"` producing
  `2026-08-19-` — but it means criteria 17-18 are load-bearing regression
  checks, not nice-to-haves. Existing slugs are untouched: nothing re-slugs an
  item that already exists (`docs/capabilities/work/retitle-a-work-item/description.md:2`).
- **Test-suite risk is low but not zero.** Criteria 21-23 are the guard: the
  existing filename-fallback assertion at `tests/test_work.py:286-287` must pass
  unchanged. If it needs editing, the derivation is doing something this spec
  did not intend — investigate before editing the test. (Editing a test is not
  *per se* a defect signal, which is why this is a risk note rather than an
  acceptance criterion.)

## Notes

**Prototype.** The precedence and every pinned edge case above were implemented
as a standalone function and run as assertions: first pass covered frontmatter,
fences, `##`, empty headings, `body is None`, the degenerate filenames,
`--title ""`, and a title ending in `#`; a second pass, added after review,
covered the nested four-backtick fence (demonstrating the bare toggle picks the
wrong heading and the char-plus-run-length rule picks the right one), the four
frontmatter-parity shapes, and the `untitled`/120-character slug floor. All
passed. The prototype lives in the session scratchpad, not in the repo — it is
evidence the rule is coherent, not the implementation.

**On the "reuse the dated stem as the slug" reading.** The issue's *Remediation*
paragraph can be read as asking for the entry's filename stem to become the
slug. It does not need to be: correcting the title alone yields exactly the slug
the issue's *Expected* section names — but, stated precisely, only because the
accept date and the entry's filed date coincide in the reproduction and no item
collides. Where they diverge — an entry filed on the 1st and accepted on the
19th — the two readings differ, and this spec takes the smaller one
(`## Non-goals`), pinning the divergence as criterion 10 rather than leaving it
implied. If the reporter meant the slug must preserve the *filing* date rather
than the *acceptance* date, that is a different change to `_unique_slug` and
`state.yaml: created`, and it should be its own item.

**Review disposition.** An adversarial review of the first draft raised the
slug-safety gap, the fence run-length defect, the frontmatter-parity divergence,
and several unverifiable criteria; all are folded in above. Two of its points
are narrowed rather than accepted whole, and both narrowings are stated where
they apply: a `~~~` line inside a backtick fence was never mis-handled by a
toggle that remembers its opening delimiter (only the *run length* was the
defect), and the claim that "no existing test depends on filename-derived
titles" was misleading rather than false — `tests/test_work.py:286-287` pins it
and still passes, which criterion 21 now says outright.

**Open question, not blocking.** With `InboxEntry.title` deliberately unchanged,
`tcw work inbox list` shows one string and `accept` produces another. A single
`accepts as: <derived title>` line in `tcw work inbox show`'s output would close
that gap for one line of code, but it changes a documented CLI surface
(`tests/test_documented_cli_surface.py`) and the capability description. Left
out of this item on purpose; worth filing separately if the mismatch confuses
anyone in practice.
