# Unify raw intake into a single artifact

Child **C1** of the initiative
[`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`][epic]. The
initiative's spec is the source of truth for the design; this request states what
C1 in particular is being asked for and why it comes first.

## Product changes

Raw input to a work item — piped text, an accepted inbox entry, a delegated
request — lands in a new artifact, `intake.md`, and stops being laundered into a
half-written `initial-request.md`.

Concretely, for a user:

- `tcw work new "t"` with nothing piped creates an item with **no** body file at
  all. Today it leaves a three-heading skeleton behind. This is the change most
  likely to surprise someone with muscle memory, and the release note has to say
  so plainly.
- `tcw work new "t"` with piped text creates `intake.md` holding that text, and
  no request.
- `tcw work inbox accept <entry>` creates `intake.md` and no longer writes a
  request document on the author's behalf. Everything it preserves today —
  attachments, the `origin`-bearing manifest, the prose fallback for an entry
  whose primary resource is binary — it must still preserve.
- `tcw work show` displays whichever of the two exists, and does not raise on an
  item that has neither.
- `tcw work list` grows a lowercase `i` for intake, ahead of `R`, so the board
  string still reads chronologically — and `R` finally means "the `request`
  stage ran" rather than "the item exists".
- Editing the body of an intake-only item creates the request and **says** it did
  so. Raw input is never edited through the body surface.

New capability `work/capture-raw-intake`; changed `work/open-a-work-item` and
`work/manage-the-work-inbox`.

## Technical changes

Four things, and the epic's spec argues each at length:

1. **An abstract intake surface on `WorkStore`.** Not a re-reading of the
   existing `body` parameter (`base.py:944`) — that would give one abstract
   argument two adapter-specific meanings, which is the litmus test failing in
   slow motion. Every caller, CLI and `serve` alike, moves to it deliberately.
2. **One canonical presence resolver**, shared by `_read_item`, `body_path`,
   `artifacts()`, the core revision, and `serve`. Presence is *exists and
   non-empty*; today `_read_item` (`fs.py:2387`) and `artifacts()`
   (`fs.py:2166-2172`) disagree, and with a fallback added that disagreement
   becomes a visible bug: an empty request beside a real intake would show no
   body *and* no letter.
3. **A write contract.** A body write always targets `initial-request.md`; on an
   intake-only item that is a promotion, announced rather than silent.
   `intake.md` is not writable through the body surface. The core revision
   (`fs.py:2904-2907`) must hash *which* file the body resolved to, or promoting
   intake to an identical-text request leaves the revision unchanged while the
   editable resource has changed.
4. **A refactor of `fs.py:2755-2769`, not its deletion.** An earlier draft of the
   epic called for deleting the synthesis block outright, which would have taken
   the manifest and binary fallback with it.

## Meta changes

**Why C1 is first.** The initiative's headline feature — a conditional template
for a `bug` item's request — cannot exist while both creation paths write
`initial-request.md` unconditionally. C1 is also the child that stands most
easily on its own: it removes a template duplicated across `fs.py:2755-2769` and
`fs.py:3016` that disagrees with itself about seeding `TBD`, and it makes the
board's `R` mean something.

**Ordering note.** `tcw work new`'s `→ edit:` hint should eventually point at
`tcw work scaffold intake`, which is C5's. Until C5 lands, C1 prints the item
path — the hint degrades rather than creating a dependency on a parallel child.

**Documentation.** C1 owns its own release note, changelog entry, README command
updates, and the correction to `skills/tcw-work/references/stage-request.md:18-19`,
which today asserts that `initial-request.md` "is the always-present body and
overview surface, so it is never absent" — the exact sentence that encoded the
model C1 replaces.

## References

- The initiative spec's `### Intake, unified` and `### The body surface: one
  presence rule, and a write contract` sections, and acceptance criteria 2, 3, 4,
  and 4b.
- `tcw/work/fs.py` — `_read_item`, `artifacts`, `body_path`, the core revision,
  `inbox accept`'s synthesis block, `update_work`.
- `tcw/work/base.py` — `WorkStore.create`, `WORK_ARTIFACTS`, the board-letter
  contract at `base.py:777-779`.
- `tcw/serve/__init__.py:764-773` and `:984-991` — the web creation and PATCH
  paths that share the surface.

[epic]: ../../active/2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven/
