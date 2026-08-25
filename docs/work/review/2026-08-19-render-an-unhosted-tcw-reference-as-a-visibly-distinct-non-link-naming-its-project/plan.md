# Plan: Render an unhosted tcw:// reference as a visibly distinct non-link naming its project

The original sequence was four code/artifact tasks, then one documentation block,
then the ledger flip at `complete`. Rework later absorbed the work-tab and
dangling-work-reference defects; where those passes disproved a detail below,
`spec.md` and `outcome.md` record the corrected contract and evidence.

## Task 1 — Record the capability back-pointer

**Creates** `docs/work/backlog/2026-08-19-render-an-unhosted-tcw-reference-as-a-visibly-distinct-non-link-naming-its-project/capabilities.yaml`:

```yaml
changed:
    - web
    - cli/reference-a-tcw-object
```

No `new:` — the spec's Capability changes section explains why this delta is two
wording flips rather than a new capability.

**Proves it:** `tcw capabilities show web` and
`tcw capabilities show cli/reference-a-tcw-object` both resolve, so the
completion gate can read the file. Task 5b applies the wording; this task only
declares it.

## Task 2 — Give `/api/resolve` a failure shape

**Modifies** `tcw/serve/__init__.py`, the `/api/resolve` branch (currently lines
957-974). Replace the flattening at 970-972 with the three-way construction from
the spec:

- `r.ok` and (`not r.project` or `r.project in self._hosted_projects()`) →
  `{"ok": True, "axis": _AXIS_WORD.get(r.axis), "key": r.key}` — unchanged.
- `r.ok` and not hosted →
  `{"ok": False, "reason": "unhosted-project", "project": r.project}`.
- otherwise → `{"ok": False, "reason": "unresolved", "detail": r.reason}`.

Compute `_hosted_projects()` lazily on the first foreign reference and reuse that
snapshot for the rest of the batch. The batch is up to `RESOLVE_MAX_URIS` (256)
URIs and the call walks `descendant_nodes`; eager computation would widen the
failure surface for empty, local-only, malformed, or dangling batches.

Add a comment stating the invariant the client depends on: `reason` is a closed
two-value discriminator, `project` is non-empty exactly when
`reason == "unhosted-project"`, `detail` is present exactly when
`reason == "unresolved"`. Task 2 does not touch `tcw/refs.py`; the later
absorbed existence fix does.

**Modifies** `tests/test_serve_resolve.py`. `_node`, `_connect`, `_start`, and
`_resolve` already exist; add:

- `test_resolve_reports_an_unhosted_descendant` — anchor + connected child,
  a work item created in the child, `_start(anchor, include_descendants=False)`;
  assert the exact object from spec criterion 1.
- `test_resolve_reports_an_unhosted_ancestor` — same graph, serve the _child_,
  resolve the anchor's item; assert `reason == "unhosted-project"` and `project`
  is the anchor's id, parameterized over `include_descendants` in `(False, True)`
  (spec criterion 2).
- `test_resolve_hosts_the_descendant_when_aggregating` — the (1) reference with
  `include_descendants=True` returns `ok: True` (spec criterion 3).
- Extend `test_resolve_foreign_and_malformed` to assert the full `unresolved`
  objects for `tcw://garbage`, `tcw://C/nope`, and `tcw://W/ghost/2026-01-01-x`
  (spec criterion 4).
- `test_resolve_failure_objects_share_one_shape` — over a batch mixing all four
  situations, assert the field invariant of spec criterion 5.

**Proves it:** `pytest tests/test_serve_resolve.py tests/test_refs.py` green;
`tcw validate` on this repo produces the same output as before the change (spec
criterion 7 — capture it before editing). The SPA still renders every failure
inert at this commit because it ignores the new fields, so the tree is
consistent.

## Task 3 — Three appearances in the viewer, and the bundle that ships them

Client source, its tests, and the rebuilt bundle land together: `pnpm check:build`
compares committed `tcw/serve/dist` against a fresh build, so splitting the
rebuild into its own commit leaves that check red in between.

**Modifies** `web/client/src/ui/shared-components.tsx`, the `Markdown` effect
(lines 51-76). Widen the response type to
`{ ok: boolean; axis?: Axis; key?: string; reason?: string; project?: string; detail?: string }`
and replace the single `else` at 70-73 with:

- `reason === "unhosted-project"` → add class `tcw-unhosted` (not `tcw-inert`),
  set `title` to `Project ${project} is not included in this board`, append a
  `<span class="tcw-project-badge">` whose text is `project` immediately after
  the anchor, and append a `<span class="tcw-sr-only">` carrying the same
  sentence with an `id`, referenced from the anchor's `aria-describedby` — so the
  sentence is both an accessible description and real text, not a `title`-only
  string (spec criterion 9). Do not trust an authored DOM marker as an ownership
  guard: every treated anchor loses its `tcw://` href, so the live query cannot
  select the same anchor twice.
- otherwise → today's behavior with the diagnosis instead of the URI:
  `classList.add("tcw-inert")`, `title = detail || uri` (the fallback covers a
  response that predates this change and an empty store-exception message).

**Modifies** `web/client/src/style.css`, after the `.body a.tcw-inert` rule
(ends line 265):

- `.body a.tcw-unhosted` — `color: var(--amber-11)`, `text-decoration:
line-through`, `cursor: not-allowed`, and a decorative
  `::before { content: "⚠ " }`. Amber's `-11` step is the Radix accessible-text
  step and is defined in both themes, matching how `--gray-11` / `--accent-11`
  are already used at lines 257-265.
- `.tcw-project-badge` — small inline chip: `var(--amber-11)` text on
  `var(--amber-3)`, `font-size: var(--font-size-1)`, `padding: 0 var(--space-1)`,
  `border-radius: var(--radius-2)`, `margin-left: var(--space-1)`.
- `.tcw-sr-only` — the standard clip-rect visually-hidden rule.

**Modifies** `web/client/src/ui/shared-components.test.tsx` — the file has no
`Markdown` coverage today. Add four tests, each stubbing `globalThis.fetch` the
way `app.test.tsx:75-79` does, rendering
`<Markdown source={'[the epic](tcw://W/orchestrator/2026-01-01-x)'} resolveLinks />`
and awaiting the resolve promise with `await screen.findBy…`:

1. `unhosted-project` → spec criterion 8 (class present, `tcw-inert` absent, no
   `data-nav-key`, badge sibling text exactly `orchestrator`).
2. the same render → spec criterion 9, via
   `screen.getByRole("link", { description: "Project orchestrator is not included in this board" })`
   plus `getByText` for the same sentence.
3. `unresolved` with `detail: "no such work item: x"` → spec criterion 10.
4. `ok: true` with `axis: "work"`, `key: "2026-01-01-x"` → spec criterion 11.

**Modifies** `tcw/serve/dist/**` — run `pnpm build` and commit its output. The
client asset filenames are content-hashed, so expect
`tcw/serve/dist/client/assets/index-*.js` and `index-*.css` to be replaced under
new names and `index.html` to change; that churn is the artifact, not a mistake.

**Proves it:** `pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint`, focused
`pnpm prettier --check` for touched files, and `pnpm check:build`. The repository-
wide prettify check and full e2e suite are baseline-red; preserve their baseline
counts and require that no committed snapshot moves.

## Task 4 — Look at it

Not automatable, so it is a task rather than a checkbox. Use the recorded
three-node fixture containing live, off-board, dangling, and malformed links,
and confirm on the work item's Initial Request tab in **both** Light and Dark
themes that the warning treatment and badge are legible and the marker is
findable by scanning, not only by hovering. Record what was seen in `outcome.md`.

## Task 5 — Documentation Sync

One pass over the finished diff, after Task 4.

**5a — the three declared entries.**

- `README.md` **[Public-API] — fires.** User-facing viewer behavior changes.
  Line 344-346 currently ends "a link to something this viewer isn't hosting
  renders inert"; replace with a sentence saying such a link is marked as
  off-board and names the project that owns it, while a link that doesn't
  resolve says why. Extend the `tcw://` links section (lines 413-436) with the
  same distinction in one sentence, next to the existing "become **in-app
  navigation** in `tcw serve`" claim.
- `docs/release-notes/upcoming.md` **[Public-API] — fires.** One entry, plain
  language: in the web app, a reference to an item on another project's board is
  now shown as off-board with that project's name beside it instead of looking
  broken, and a genuinely broken reference now says what is wrong with it. No
  module names, no `reason`/`detail` field names.
- `docs/changelogs/upcoming.md` **[Any-Code-Change] — fires.** Under **Changed**:
  the `/api/resolve` failure shape (`reason` / `project` / `detail`, the closed
  two-value discriminator) and the `tcw-unhosted` / `tcw-project-badge`
  rendering path. Under **Fixed**: the resolver's computed reason and owning
  project were discarded at `tcw/serve/__init__.py`, collapsing four situations
  into one appearance. Note the rebuilt `tcw/serve/dist`.
- `skills/<component>/SKILL.md` **[Skill-Driven-Component] — does not fire.**
  No skill drives `tcw serve`; the CLI surface, the work model, the lifecycle,
  and every guardrail are untouched. The "Web editing" notes in
  `skills/tcw-work/SKILL.md` and `skills/tcw-capabilities/SKILL.md` describe
  editing and hooks, not link rendering, and stay true verbatim. Record this
  evaluation in `outcome.md` rather than editing a skill to no purpose.

**5b — the ledger flip, at `complete` and not before.**

- `docs/capabilities/web/description.md` — retain the true unresolved-target
  behavior and extend it with the distinction: a real work target in the graph
  but outside the served board is shown off-board and names its project.
- `docs/capabilities/cli/reference-a-tcw-object/description.md` — extend
  "`tcw serve` turns hosted targets into in-app navigation" to say what it does
  with an unhosted one.
- Both are body edits, so `tcw capabilities set … --field` does not apply;
  statuses stay `Supported` and no `--status` flip is needed. Run
  `tcw capabilities check` after (spec criterion 15).

## Verification

What the suite cannot decide, for the `verify` stage:

- **Legibility and loudness.** Task 4's manual look. The spec's stated risk is
  that the new treatment is _too_ loud on a cross-node document; the judgment
  call is whether a document with several off-board references reads as
  informative or as alarming. If it is alarming, the dial is the CSS.
- **Wording.** `Project <id> is not included in this board` is a sentence a user
  reads. Confirm it says the right thing for both reproduction shapes — a
  descendant not aggregated, and an ancestor from a child — where "this board"
  means the served node, not the project the reader came from.
- **The accepted disclosure.** Confirm the narrower threat model in the spec:
  loopback and Origin/CSRF controls are not caller authentication, so any local
  process that can reach the port can read the served node's error detail.
- **Snapshot silence.** Spec criterion 14 asserts the e2e snapshots do not move.
  That is an expectation from reading the snapshot names, not a fact checked
  before the change; if `pnpm test:e2e` reports a diff, it is evidence to explain,
  not a snapshot to bless.

## Notes

- Every spec acceptance criterion is claimed by exactly one task: 1-7 → Task 2,
  8-11 → Task 3 tests, 12-14 → Task 3 gates, 15 → Task 5b.
- Litmus: no task adds or changes a store operation. Task 2 reads
  `resolve_tcw_ref`'s existing result and the server's existing hosting set; both
  already have abstract analogs, and no filesystem concept reaches the response.
