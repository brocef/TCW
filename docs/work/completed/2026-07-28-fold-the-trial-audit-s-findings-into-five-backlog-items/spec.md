# Spec: Fold the trial audit's findings into five backlog items

## Capability changes

**New:** `work/retitle-a-work-item` — "Retitle a work item", seeded `Missing`,
`Subject: work-item`, `Planning doc` pointing at this item. Flipped to
`Supported` at completion.

The ledger already gives each `tcw work edit` flag its own capability
(`work/prioritize-a-work-item`, `work/tag-a-work-item`,
`work/estimate-a-work-items-effort-and-complexity`), so `--title` follows that
shape rather than being folded into an existing entry. No `Feature` pointer:
none of the sibling `work/*` edit capabilities carry one.

Contradiction check: `tcw capabilities search title` turns up nothing claiming a
work item's title is fixed after creation, and `web/editing` already states the
web app can edit work items — so a CLI retitle closes a gap between the two
surfaces rather than contradicting either. `tcw capabilities check` is clean.

## Problem

The 2026-07-28 trial of the backlog-audit procedure produced code-verified
findings on four still-open backlog items. They live only in a chat transcript.
The findings are not restatements of what the items already say — three of them
**contradict** a claim the target item makes about the code, so leaving them
unrecorded means the next person to spec those items starts from a false premise.

## Goals

- Each of the four target items carries its findings inline, with citations that
  resolve in the current tree.
- Contradictions are recorded as corrections *inside* the item, at the claim they
  correct, so a spec writer cannot read the wrong sentence without the correction
  attached.

## Non-goals

- Re-running the audit. Findings come from the trial run, re-verified below.
  Re-verification may correct or extend a finding at the code it already points
  at — one such correction is recorded in Design — but no target item is audited
  afresh and no item outside the four is examined.
- Changing what any target item *is*. A finding that would redraw an item's
  boundary gets raised, not absorbed.
- Acting on the findings. Writing "`create` is test-only, consider collapsing it"
  into an item is transcription; collapsing it is that item's own work.
- Re-opening the `remote`-tag parking decision (settled 2026-07-28: all three keep
  their items at priority 10) or the `typed-taxonomy-relations` discard.
- Any CLI work beyond the single `--title` flag: no slug rename, no `--title` on
  other subcommands, no general "edit any field" surface, no change to
  `update_work` or the store. The flag exists here only because the retitle this
  item owes cannot otherwise be done through a command.
- A systematic sweep for other phantom CLI verbs in the docs. This spec found one
  and fixes the gap behind it;
  `2026-07-28-scan-every-markdown-file-for-phantom-cli-verbs-excluding-archives`
  owns the sweep.

## Design

Four edits to four `initial-request.md` files, plus one retitle — and, because
no CLI verb can perform that retitle today, the missing `--title` flag.

### Re-verification results

Every citation from the trial run was re-checked against the working tree. All
line anchors resolve exactly as cited — the trial run's disclosure that it never
re-checked its subagents' citations turned out not to matter for the line numbers.
Two *claims* failed, both recorded below.

| Finding | Verdict |
|---|---|
| `FsWorkStore.create` writes unprotected (`fs.py:2288-2295`) | **Confirmed** — `write_text` + `dump_yaml`, no `_atomic_write` |
| …declared abstract at `base.py:931` | **Confirmed** |
| …sole caller is `tests/test_recursion.py` | **FAILED** — see below |
| `accept_inbox` fix precedent (`fs.py:2246-2269`) | **Confirmed** — `mkdtemp` → populate → `os.replace` → `rmtree` on except |
| `node_root = root.parent.parent` (`fs.py:578-585`) | **Confirmed** (`fs.py:579`) |
| `start --force` already exists (`cli.py:982`) | **Confirmed** — "start despite unresolved blockers" |
| Move committed inside `_effect_transition` | **Confirmed** — `fs.py:2321-2322` calls `_commit_transition` |
| `Term.origin` is a single alias used as a dict key (`fs.py:893`, `base.py:156-158`) | **Confirmed** — also `fs.py:863`; declared `base.py:152` |
| Cycles already guarded at any depth (`fs.py:656-664`, `868-884`) | **Confirmed** |
| `taxonomy/federate-shared-vocabulary` is Partial with a matching Gaps line | **Confirmed** — Gaps names "transitive (multi-level) extends" |
| Editor item's `state.yaml` title still says "vendored" | **Confirmed, reframed** — see below |
| Retitle via `tcw work edit … --title` | **FAILED** — no such flag; see below |

**Failed claim 1 — "sole caller `tests/test_recursion.py`".** `.create(` appears
across 17 test modules, every one of which constructs an `FsWorkStore`. The
substantive claim survives in corrected form: `create` has **no production
caller** — nothing under `tcw/` calls it. Both production paths (`cli.py:216`,
`serve/__init__.py:773`) go through `create_work` (`fs.py:2410`). So "collapse it
into `create_work`" remains a live option, but it is a test-surface migration,
not a one-file change. The finding is transcribed with that correction, not as
originally worded.

**Reframed finding — the "vendored" title.** The trial run recorded the title as
"contradicted by the item's own body". The body does not contradict it; it
*pre-empts* it. `initial-request.md:3-6` already carries a `> **Title note:**`
explaining that "vendored" is historical, that the web client is now a built
React app, and that "The slug is kept for stability." So the item is not
misleading a reader today. What the note defends, though, is the **slug** — and
nothing argues the *title* must stay stale, while the title is what `tcw work
list` and the board actually display. The retitle stands as a real improvement,
but as a display-accuracy fix, not as the repair of a live contradiction. It is
transcribed that way.

Consequence for scope: `update_work` writes only `state.yaml`'s title
(`fs.py:2588-2590`); it does not touch the body's `# ` heading. So the retitle is
two changes — the flag sets the state title, and the body H1 plus the now-partly
redundant Title note are edited as part of finding 4's transcription.

**Failed claim 2 — the retitle command.** `tcw work edit` has no `--title` flag
(`cli.py`: edit takes only `--blocked-by/--blocks/--unblocked-by/--priority/
--effort/--complexity/--initiative/--tag/--untag`). `update_work(title=…)` exists
in the store and `tcw serve` reaches it (`serve/__init__.py:991`), but no CLI verb
does. This is itself an instance of
`2026-07-28-scan-every-markdown-file-for-phantom-cli-verbs-excluding-archives`.
The route is settled in Notes; the retitle itself stays in this item either way.

### ~~Bonus finding~~ — withdrawn during implementation

This spec claimed `create_work`'s two-write gap (`fs.py:2498-2501`) as a new
finding "that matters more, because it is on the path users actually hit". It is
**already the target item's first bullet** — that item's `initial-request.md:14-16`
names `create_work` and describes the exact `mkdir` → `_atomic_write` →
`_atomic_write` shape with no rollback.

Verifying the code without re-reading the item the finding was destined for is
the same mistake, in miniature, that this whole item exists to clean up after.
Withdrawn — and nothing is lost: the genuinely new material for that item is
`FsWorkStore.create` (a write site it does not list, and the weaker one — no
`_atomic_write` at all) plus the `accept_inbox` precedent.

### The four edits

1. **`2026-07-03-transactional-multi-file-writes-in-the-fs-store`** — add the
   `create` write site (corrected: no production caller, eight test modules), the
   `create_work` bonus finding, and the `accept_inbox` precedent to point the
   implementer at.
2. **`2026-06-22-concurrency-safe-work-claims-…`** — correct the item's own
   "`FsWorkStore` already takes `root` as a parameter, so this is the only new
   branching" claim (`initial-request.md:42-43`) in place; add the `--force`
   name collision and the `_effect_transition` commit-ordering consequence for
   the post-move owner stamp.
3. **`2026-07-01-transitive-taxonomy-inheritance`** — add that `Term.origin`'s
   encoding is a spec decision; strike cycle-guarding from the scope; link the
   `federate-shared-vocabulary` capability Gaps line.
4. **`2026-07-02-add-a-vendored-rich-markdown-editor-…`** — retitle to drop
   "vendored", keeping the slug.

### The `--title` flag

`update_work` already accepts `title` and already carries the revision guard
(`fs.py:2517-2523`), and `tcw serve` drives it that way (`serve/__init__.py:991`).
The CLI is the only surface missing it, so this is an argparse option on the
`edit` subparser plus a dispatch line — no store change, no new validation path.
The slug is derived at creation (`_unique_slug`) and is not recomputed on update,
so a retitle leaves the stable ID alone; that is existing behavior being exposed,
not new behavior.

Deliberately minimal: no `--title` on any other subcommand, no slug-rename
option, no interactive prompt. `tcw work new` already takes a title positionally.

## Acceptance criteria

- `2026-07-03-transactional-multi-file-writes-in-the-fs-store` names `create`
  (`fs.py:2288-2295`) as a write site and `accept_inbox` (`fs.py:2246-2269`) as
  the precedent. (It already named `create_work`; see the withdrawn finding.)
- That item states `create` has no caller under `tcw/`, and that `.create(`
  appears across 17 test modules (every one of which constructs an
  `FsWorkStore`) — rather than repeating the trial run's "sole caller
  `tests/test_recursion.py`". The exact work-store subset is left for that item
  to enumerate when it costs something.
- `2026-06-22-concurrency-safe-work-claims-…` no longer asserts unqualified that
  the resolved root is the only new branching; the correction cites
  `fs.py:578-585` and names git ops, the sentinel reader, and hook cwd as the
  other consumers of `node_root`.
- That item records that `start --force` is taken (`cli.py:982`) and that the
  owner stamp lands as a second commit after `_effect_transition`.
- `2026-07-01-transitive-taxonomy-inheritance` states that `Term.origin` is a
  single alias used as a dict key and that its multi-hop encoding is a spec
  decision; states cycles are already guarded (`fs.py:656-664`, `868-884`) and
  out of scope; links `taxonomy/federate-shared-vocabulary`.
- `tcw work edit <slug> --title "<new title>"` sets the title, and `tcw work edit
  --help` lists the flag. A test covers the round-trip: retitle, then `get_detail`
  reports the new title and the unchanged slug.
- The editor item's `state.yaml` title and its body `# ` heading both contain no
  "vendored"; its slug is unchanged; its Title note reads correctly against the
  new title rather than explaining a discrepancy that no longer exists.
- The retitle was performed with the new flag, not by hand-editing `state.yaml`.
- `work/retitle-a-work-item` exists and reads `Supported` at completion;
  `capabilities.yaml` lists it under `new:`; `tcw capabilities check` passes.
- `README.md`, `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`,
  and `skills/tcw-work/references/commands.md` describe the new flag.
- Every file:line citation written into an item resolves to the claimed code in
  the tree at completion time.
- No target item gains or loses a goal, only claims and citations.

## Risks

- **Line drift.** Citations are pinned to a tree that keeps moving. Mitigation:
  every citation carries the symbol name, not just the line — a reader who finds
  drift can still locate the code.
- **Absorbing scope by accident.** The `create` finding invites "so just delete
  `create`", which is a decision for the transactional item, not this one.
  Mitigation: findings are written as options with their cost, never as decisions.
- **Silent no-op.** All four edits are prose; nothing fails if one is skipped.
  Mitigation: the acceptance criteria above are per-item and checkable by grep.

## Notes

- **Settled — how to retitle the editor item.** No CLI verb retitles an existing
  item. Routes considered: add `--title` to `tcw work edit` here; retitle through
  `tcw serve`; retitle via a one-off store call; or defer the retitle to a
  follow-up. **Decided: add the flag here** (user, 2026-07-28). The item is a
  transcription item and this is a code change, so the widening is deliberate and
  recorded rather than absorbed — it is bounded by the Non-goals above. The
  trade accepted: a docs item now carries a test, a changelog entry, a release
  note, and a capability flip.
- The retitle is a display-accuracy fix, not the repair of a live contradiction —
  the editor item's body already explains the stale word (see Design). Anyone
  re-reading this item later should not conclude the board was misleading users.
- The `## Meta changes` section of `initial-request.md` records the `remote`-tag
  decision as settled. Nothing in this spec revisits it.
