# Spec — Unify raw intake into a single artifact

Child **C1** of the initiative
`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`. The initiative's
spec settles the shape; this one settles the implementation and the checks.

All line references are to the tree at `ae23f0a` and were read, not recalled.
Note that the initiative spec cites `fs.py` and `base.py` without their package
path: the files are `tcw/store/fs.py` and `tcw/store/base.py`.

## Capability changes

| Delta       | Capability                   | Note                                                              |
| ----------- | ---------------------------- | ----------------------------------------------------------------- |
| **New**     | `work/capture-raw-intake`    | Seeded `Missing` at planning, flipped `Supported` by this item.   |
| **Changed** | `work/open-a-work-item`      | Its current text is the model this item removes — see below.      |
| **Changed** | `work/manage-the-work-inbox` | "generates the durable `initial-request.md`" becomes false.       |

`work/open-a-work-item` currently reads: "`initial-request.md` is always-present
and serves as both the body/overview surface and the canonical request artifact."
That sentence is the ledger's statement of exactly the model this item replaces,
which is a good sign the boundary is drawn in the right place.

Taxonomy: `work-item` (Vocabulary) and `work-inbox` (Feature) both exist and
cover this. **No new term.** `intake` is an artifact of a work item, not a new
noun in the registered vocabulary — the initiative adds `work-item/lifecycle-hook`
in C3 because a hook genuinely had no term; intake does not have that problem.
`work/capture-raw-intake` links `Feature=work-inbox` and `Subject=work-item`.

## Problem

Three creation paths produce a work item, and they disagree about what the item
starts with.

1. **`create_work` templates a request unconditionally** (`fs.py:3015-3018`):

   ```python
   body_content = (
       f"# {title}\n\n## Product changes\n\n## Technical changes\n\n## Meta changes\n\n"
       f"{body}\n"
   )
   ```

   Every item ever created therefore has an `initial-request.md`, whether or not
   its `request` stage has run. With no stdin, `body` is `""` and the file is a
   bare heading skeleton.

2. **`inbox_accept` templates a second, different request** (`fs.py:2756-2761`) —
   same three headings, but seeded `TBD`, plus an `## Inbox contents` section
   carrying the manifest and the entry body. Two hardcoded templates that
   disagree with each other about `TBD`, in one file, ~250 lines apart.

3. **`delegate` / `escalate`** deposit raw text into the inbox and let `accept`
   ingest it. This one is right, and is the pattern the other two adopt.

The consequence is that **`R` on the board means "an item exists"**, not "the
request stage ran". `_render_board_item` (`work/cli.py:314-322`) maps
`initial-request` → `R`, and `artifacts()` reports it present for any item whose
skeleton is non-empty — which the template guarantees, since it always contains
at least the title heading.

**Two presence rules, and they disagree.** `artifacts()` requires non-whitespace
content (`fs.py:2172`):

```python
present = p.is_file() and bool(p.read_text(encoding="utf-8").strip())
```

while `_read_item` accepts mere existence (`fs.py:2387`):

```python
body=request.read_text(encoding="utf-8") if request.exists() else "",
```

and `get_detail`'s core revision uses a third spelling of the same idea
(`fs.py:2906-2907`). Today the disagreement is invisible, because the template
makes an empty request impossible. Add a fallback to `intake.md` and it becomes a
visible bug: an empty `initial-request.md` beside a real `intake.md` would show
no body **and** no letter.

**`body` is one abstract argument that would acquire two meanings.**
`WorkStore.create(..., body=…)` (`base.py:944`) is an abstract primitive.
Redirecting it to `intake.md` inside the FS adapter, while a Jira adapter writes
the same argument to a description field, is the prime directive's litmus test
failing quietly: the caller can no longer tell what it asked for.

## Goals

1. Raw input lands in `intake.md`; no code path synthesizes a request document.
2. One presence rule, defined once, used by every reader.
3. A body write always creates or updates the request, never mutates intake, and
   says when it promoted an item.
4. Everything `inbox_accept` preserves today it still preserves: attachments, the
   `origin`-bearing manifest, and the binary fallback prose.
5. Existing items are untouched. No backfill.

## Non-goals

- **Scaffolding.** `tcw work scaffold intake` is C5's. C1 leaves `tcw work new`
  printing the item path rather than a file path.
- **The JSON projection.** C2's. C1 must not add a second projection on the way
  past.
- **Templates, hooks, roles, conditions.** C3–C6.
- **The `stage-request.md` router rewrite.** C1 corrects the one sentence it
  falsifies (`skills/tcw-work/references/stage-request.md:18-19`); the wholesale
  rewrite is C7's.
- **Backfilling intake for existing items.** An item that never had raw input
  should not be given a fabricated one.

## Design

### The abstract surface: one new creation argument, and nothing else

`intake` joins `WORK_ARTIFACTS` (`base.py:780`), **appended** as that tuple's
comment requires:

```python
WORK_ARTIFACTS = ("initial-request", "spec", "plan", "outcome", "refined-outcome",
                  "rework", "post-mortem", "intake")
```

Appending is what the existing letter-order contract demands, and it costs
nothing here because the board renderer orders letters itself (below).

**That is the whole read/write surface for intake.** `read_artifact` and
`write_artifact` (`base.py:1111-1126`) are already abstract, already bounded by
`WORK_ARTIFACTS`, and already raise on unknown names — so once `intake` is a
registered artifact name, reading and editing it are covered. No new method.

The one thing genuinely missing is **creating an item whose starting content is
intake**. That gets an explicit keyword on the two creation primitives:

```python
def create(self, title, created=None, body="", priority=None, parent=None,
           intake: str = "") -> WorkItem
def create_work(self, title, *, ..., intake: str = "") -> WorkDetail
```

- `body` keeps its existing meaning: the **request** document. `serve`'s creation
  form (`serve/__init__.py:764-776`) passes a body the user typed as a request,
  and it keeps doing exactly that.
- `intake` is raw, unprocessed input. Non-empty → the adapter writes `intake.md`
  verbatim.
- Both empty → **neither file is written.** This is the behavior change.
- Both non-empty is legal and writes both; no caller does it today, and
  forbidding it would be a rule with no reason behind it.

A separate argument rather than a re-read of `body` is the litmus test applied
rather than dodged: a remote adapter can put intake in a description field, a
comment, or an attachment, and it still knows which one it was handed.

**Why a creation argument and not create-then-`write_artifact`.** Both creation
paths are atomic today — `create_work` builds the folder and rolls it back on any
failure (`fs.py:3028-3035`), `inbox_accept` assembles a temp directory and
`os.replace`s it into position (`fs.py:2764-2775`) — and a two-step sequence
would leave an item observable with no intake, plus a failure mode where the
intake write fails after the item exists. The argument keeps creation one
operation, which is a property any store can honor.

### The canonical presence resolver

One private helper on the FS adapter, and every reader routes through it:

```python
_BODY_ORDER = ("initial-request", "intake")

def _resolve_body(self, d: Path) -> tuple[str | None, str]:
    """(artifact name, text) for the item's body surface, or (None, "")."""
```

Presence is **exists and non-empty after `.strip()`** — `artifacts()`'s rule
(`fs.py:2172`), which is the stricter and the correct one; mere existence lets an
empty file claim a stage ran. Resolution order is `initial-request.md` →
`intake.md` → `(None, "")`.

Callers converted:

| Site                                | Today                                | After                                       |
| ----------------------------------- | ------------------------------------ | ------------------------------------------- |
| `_read_item` (`fs.py:2387`)         | `request.exists()`                   | `_resolve_body(d)[1]`                       |
| `artifacts()` (`fs.py:2166-2177`)   | its own inline rule                  | the helper's rule, per artifact             |
| `body_path` (`fs.py:2158-2160`)     | always `initial-request.md`          | the resolved file, or `None` when neither   |
| `get_detail` (`fs.py:2904-2907`)    | request text only                    | resolved name **and** text (below)          |
| `serve`                             | via the store                        | unchanged — it already goes through these   |

`body_path` returning `None` on a both-absent item is the one signature-level
change, and it is already a `Path | None` return, so no caller gains a new case
it did not have to handle. **Both-absent must return an empty body, not raise** —
criterion 4 of the initiative.

### The write contract

`update_work(body=…)` targets `initial-request.md` (`fs.py:3057`) and keeps
targeting it. **Writes do not follow the read fallback.** The reasoning is not
symmetry: on an intake-only item, following the fallback would either mutate raw
input or silently satisfy the `request` stage — and `serve`'s PATCH path
(`serve/__init__.py:984-985`) shares the same code, so the web editor would do it
too.

- Body write on an item with a request → update, as today.
- Body write on an **intake-only** item → **promotion.** It creates
  `initial-request.md`, leaves `intake.md` byte-identical, and reports the
  promotion: `WorkDetail` carries `promoted: bool`, and `serve`'s PATCH response
  surfaces it as `"promoted": true`.

  **Corrected during implementation.** An earlier draft of this spec had
  `tcw work edit --body` printing the promotion on stderr. There is no such
  flag — `tcw work edit` sets title, estimates, tags, and blocking links only,
  and the CLI has no body-write path at all. `update_work`'s callers are
  `serve`'s PATCH handler and nothing else; on the filesystem an agent writes
  `initial-request.md` directly, where the promotion is self-evident from the
  file appearing. Adding a `--body` flag to satisfy a criterion is scope this
  item was not asked for, so the contract lives where the writes actually go.
- `intake.md` is never reachable through the body surface. It is editable only
  via `write_artifact("intake", …)`, because raw input that quietly changes is
  not raw input.

`promoted` in the PATCH response is additive; `serve`'s existing keys keep their
shapes (`serve/__init__.py:996-1000`). C2 is the child allowed to change that
payload's shape, and it is deliberately not doing so here.

### The core revision

`get_detail` hashes `state.yaml` + the request text (`fs.py:2904-2907`). With the
fallback it must hash **state + which artifact the body resolved to + its text**:

```python
name, body_text = self._resolve_body(d)
core_rev = _revision_multi(state_text, name or "", body_text)
```

Without the name in the hash, promoting an intake to a request with identical
text produces an unchanged revision while the editable resource has changed —
which would let a `core_revision`-guarded write (`fs.py:3050-3055`, and every
`serve` PATCH) succeed against a stale view of what it was editing.

This changes the revision token for every existing item on first read. That is
harmless: the token is compared within a session, never persisted, and a mismatch
surfaces as `StaleRevision` on a concurrent write rather than as corruption.

### The board

`_render_board_item` (`work/cli.py:314-322`) gets `"intake": "i"`. Its loop walks
`st.artifacts()` in `WORK_ARTIFACTS` order, which now ends with `intake` — so a
naive addition renders `Ri`, not `iR`.

**The renderer sorts the letters into lifecycle order**, with `intake` first:

```python
_BOARD_ORDER = ("intake", "initial-request", "spec", "plan", "outcome",
                "refined-outcome", "rework", "post-mortem")
```

This is display order, held in the renderer, and it is deliberately not
`WORK_ARTIFACTS` reordered — that tuple's comment forbids insertion, and the
constraint it protects (never shifting an existing item's display) is satisfied
by putting the new letter in front in lowercase, where it cannot be confused with
an existing one. The `labels.get(..., "?")` fallback stays: an artifact added to
the registry with no letter must not crash the board.

### `inbox_accept`, refactored not deleted

`fs.py:2756-2761` synthesizes a request. It is replaced by intake assembly that
keeps every preserved thing:

```python
intake = ("## Inbox manifest\n\n" + "\n".join(manifest_lines)
          + "\n\n## Inbox body\n\n" + body + "\n")
```

- The **manifest** (`fs.py:2751-2755`) is kept verbatim, including its
  `— accepted from \`<origin>\`` suffix. The manifest entry that today reads
  `initial-request.md` becomes `intake.md`, in both the manifest list
  (`fs.py:2745`) and the suffix test (`fs.py:2753`).
- The **binary fallback** (`fs.py:2755`) — `"Binary intake preserved as an
  attachment."` when `detail.body is None` — is kept verbatim. An
  attachments-only entry still produces an `intake.md`, carrying the manifest and
  the note.
- **Attachments** (`fs.py:2770-2773`) and the temp-dir/`os.replace` atomicity are
  untouched.
- The `# {accepted_title}` heading and the three `TBD` headings are dropped. The
  title lives in `state.yaml`; the headings were the request template.
- Demoted from headings to `##`: the sections were `###` under an
  `## Inbox contents` parent that no longer exists.

### `tcw work new`

`_new` (`work/cli.py:224`) passes `body=_stdin_body()`; it passes
`intake=_stdin_body()` instead. `_stdin_body` (`work/cli.py:88-95`) is unchanged
and its behavior is the stated encoding policy: it `read()`s text through
Python's default decoding and swallows `OSError`/`ValueError` as `""`. So the
promise is *the decoded stdin text*, not *exactly the piped bytes* — an interface
that returns `str` and eats read errors cannot promise bytes.

The `→ edit:` hint (`work/cli.py:240-242`) currently prints `body_path`, which
now returns `None` for an item with neither artifact — so the hint simply does
not print, and the existing `if body is not None` guard already handles it. For
an intake-only item it prints the intake path, which is correct: that is the file
there is to look at. C5 replaces this with a `tcw work scaffold intake` hint.

## Acceptance criteria

Numbered locally; the initiative's criteria 2, 3, 4, and 4b are the source.

1. `tcw work new "t"` with no stdin creates an item folder containing exactly
   `state.yaml` — no `initial-request.md`, no `intake.md`. Asserted by listing
   the folder, not by checking two paths.
2. `tcw work new "t"` with piped stdin creates `intake.md` whose content is the
   decoded stdin text and no `initial-request.md`.
3. `tcw work inbox accept` creates `intake.md` and no `initial-request.md` for
   **all three** entry shapes — a text file, a folder with an `INDEX.md` plus
   resources, and a binary-only entry — with attachments copied, the manifest
   naming `intake.md` with its `— accepted from` suffix, and the binary fallback
   prose present in the third case.
4. `grep -rn "## Product changes" tcw/` matches nothing outside tests. No code
   path synthesizes a request document.
5. The board shows: nothing for a fresh item, `i` for an intake-only item, `iR`
   after a request is written, and `R` for a legacy item with a request and no
   intake. All four asserted in one test.
6. `tcw work show` displays the intake on an intake-only item, the request once
   one exists, and an empty body **without raising** on an item with neither.
7. An empty `initial-request.md` beside a non-empty `intake.md` displays the
   intake and shows `i` — one rule governing both surfaces.
8. A body write on an intake-only item writes `initial-request.md`, leaves
   `intake.md` byte-identical (compared as bytes), and reports
   `promoted: True`; a second body write on the same item reports `False`.
   Verified through `serve`'s PATCH path, which is the only caller of
   `update_work` — see the correction under "The write contract".
9. Promoting an intake to a request with **identical text** changes the core
   revision.
10. `write_artifact(slug, "intake", …)` succeeds; a body write never touches
    `intake.md`.
11. **Migration:** an item folder created before this change — request present,
    intake absent — reads with the same body, the same board letter, and the same
    `artifacts()` result as before. The existing suite passing unmodified is
    part of this criterion, excluding tests that assert the old creation
    template.
12. `tcw capabilities check`, `tcw capabilities drift`, and `tcw validate` are
    clean, with `work/capture-raw-intake` flipped to `Supported`.

## Risks

- **Muscle memory.** `tcw work new` no longer leaves a file to open. No test
  covers a user's expectations; the release note must lead with this, and it is
  worth typing by hand before completing. The initiative's plan names this
  explicitly under "what the suite cannot check".
- **A test corpus that encodes the old template.** Any test asserting the three
  headings after `create_work` is asserting the defect. Each such change is
  deliberate and named in `outcome.md` rather than swept.
- **`body_path` returning `None` more often.** Every caller already handles
  `None`, but the guard is easy to lose in a refactor. Criterion 6 covers the
  `show` path; a grep for `body_path` at implementation time covers the rest.
- **Revision-token churn on first read.** Explained above and assessed harmless;
  recorded here so it is not rediscovered as a bug.
- **`serve` shares every one of these paths.** The web editor's create and PATCH
  routes go through `create_work` and `update_work`, so a store-level test alone
  does not prove `serve` is right. Criterion 8 tests the PATCH path directly.

## Notes

- The initiative spec's file references omit the `tcw/store/` package path
  (`fs.py:2755` = `tcw/store/fs.py:2755`). The line numbers themselves check out.
- `read_artifact` / `write_artifact` already existing is the reason this child's
  abstract surface is one keyword argument rather than a new interface. Worth
  recording: the epic's plan describes "an abstract intake surface" in a way that
  reads as larger than what the code turned out to need.
