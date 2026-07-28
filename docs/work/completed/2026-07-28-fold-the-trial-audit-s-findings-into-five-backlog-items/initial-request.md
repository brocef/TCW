# Fold the trial audit's findings into five backlog items

## Origin

A trial run of the new backlog-audit procedure on 2026-07-28 (12 subagents over
11 items) produced substantive, code-verified findings on five backlog items that
the earlier sequential audit missed. They currently exist **only in a chat
transcript**, which is exactly the kind of loss the work system exists to
prevent.

This is transcription of verified findings into the items they belong to — not
new analysis.

## Product changes

None. Editing work-item requests.

## Technical changes

Fold each finding into the named item's `initial-request.md`. Every one was
verified against the working tree by the trial run; **re-verify before writing**,
since the trial agent disclosed it never re-checked its own subagents' citations,
and two of its headline claims turned out wrong.

### `2026-07-03-transactional-multi-file-writes-in-the-fs-store`

- A **fourth** unprotected write site: `FsWorkStore.create` (`fs.py:2288-2295`)
  uses plain `write_text`, not even `_atomic_write`. Declared abstract at
  `base.py:931` but reportedly test-only (sole caller `tests/test_recursion.py`)
  — confirm, then decide whether collapsing it into `create_work` is the smaller
  diff than protecting it.
- A **fix precedent already in-repo**: `accept_inbox` (`fs.py:2246-2269`) does
  `mkdtemp` → populate → `os.replace` → `rmtree` on except. Point the implementer
  at it rather than letting them design a new helper.

### `2026-06-22-concurrency-safe-work-claims-…`

- The request claims "`FsWorkStore` already takes `root` as a parameter, so this
  is the only new branching." Reportedly false: `FsTreeStore` derives
  `node_root = root.parent.parent` (`fs.py:578-585`), and `node_root` is what git
  operations, the sentinel reader, and hook cwd all key off — including the
  sentinel that would hold `work.path` itself, which makes it config-reads-config.
- `start --force` **already exists** with different semantics ("start despite
  unresolved blockers", `cli.py:973`), so the proposed take-over flag needs a
  different name.
- The move is now committed inside `_effect_transition`, so a post-move owner
  stamp lands as a second commit rather than riding along with the transition.

### `2026-07-01-transitive-taxonomy-inheritance`

- `Term.origin` is a single alias used as a dict key (`fs.py:893`,
  `base.py:156-158`), so a two-hop origin has no representable value — the
  encoding is a design decision the spec must make, not an implementation detail.
- Cycles are **already** guarded at any depth (`fs.py:656-664`, `868-884`), so
  that is not part of the work.
- `tcw capabilities show taxonomy/federate-shared-vocabulary` is `Partial` with a
  Gaps line already naming this — link it.

### ~~`2026-06-19-typed-taxonomy-relations`~~ — closed 2026-07-28

This finding was acted on rather than transcribed. `docs/plan/phase-2-taxonomy.md:157`
explicitly defers typed relations on YAGNI grounds: *"deferred until a consumer
needs them (the tool reads pointers, humans write meaning)"* — a recorded
decision, not an absence of demand. No consumer appeared, so the item was
**discarded** in the 2026-07-28 audit. Four items remain to fold, not five; the
slug keeps "five" for stability.

Leave `phase-2-taxonomy.md:157` in place — it is the evidence for the discard,
not a duplicate of the dropped item.

### `2026-07-02-add-a-vendored-rich-markdown-editor-…`

- `state.yaml`'s title still says "vendored", contradicted by the item's own body.
  Retitle with `tcw work edit … --title "Add a rich Markdown editor to the local
  web app"`, keeping the slug.

## Meta changes

Also unrecorded and worth a decision, though not item-specific: **the three
`remote`-tagged items are parked by a single standing directive** (AGENTS.md:42,
`phase-6-beyond.md:3`) yet each accrues maintenance notes on every audit cycle
while none can start. That is one decision about the `remote` tag, not three about
individual items. Raise it rather than re-auditing them indefinitely.

**Decided 2026-07-28:** raised and settled. All three keep their items and sit at
**priority 10**, the bottom band, which is now the park marker — the path stays
on file in `phase-6-beyond.md` and the refreshed model notes are preserved, at no
cost. Do not re-open this per-item; a future audit that wants to change it is
changing one decision about the `remote` tag.

## Acceptance criteria

- Each of the four remaining items carries its findings, with citations
  re-verified. (The fifth, `typed-taxonomy-relations`, was discarded instead.)
- Any finding that fails re-verification is dropped and the failure noted here.
- No item's scope is silently widened — a finding that changes what an item *is*
  gets raised, not absorbed.
