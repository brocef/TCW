# Spec: Render an unhosted tcw:// reference as a visibly distinct non-link naming its project

## Capability changes

No new capability. The delta changes how an existing capability _behaves_, not
what a user can do: reading a document in `tcw serve` is already
`web` (`cap-9d225a`), and writing the link is already
`cli/reference-a-tcw-object` (`cap-65e549`). Before closeout, both descriptions
omitted the new distinction, so both are `changed:` — a wording extension at
`complete`; statuses stay `Supported`.

- **changed — `web`.** The existing statement that unknown, unregistered, or
  dangling targets remain inert is still true. Extend it to say that a real work
  target in the registered graph but outside the served board is shown as
  off-board and names its owning project, while an unresolved reference states
  why it failed.
- **changed — `cli/reference-a-tcw-object`.** Before closeout, its body said
  "`tcw validate` checks resolution and `tcw serve` turns hosted targets into
  in-app navigation." True but silent on the other half; extend it to say what
  `serve` does with a target it does not host.

Recorded as the work→capability back-pointer in the item's `capabilities.yaml`
under `changed:`. No taxonomy delta: the terms involved (`reference`) and the
feature (`connected-project-registry`) already exist and are unchanged.

## Problem

`POST /api/resolve` computes both _why_ a reference failed and _which project_
owns it, then throws both away. `tcw/serve/__init__.py:969-972`:

```python
r = resolve_tcw_ref(self.server.node_root, uri)
ok = r.ok and (not r.project or r.project in self._hosted_projects())
result[uri] = ({"ok": True, "axis": _AXIS_WORD.get(r.axis), "key": r.key}
               if ok else {"ok": False})
```

`resolve_tcw_ref` already returns a populated `reason` on every failure and a
populated `project` on every foreign work reference (`tcw/refs.py:44-46`,
`104-129`) — `qualified_work_ref_problem` even distinguishes "no such project in
this graph" from "no such work item" (`tcw/store/fs.py:277-299`). `tcw validate`
consumes that reason and prints it (`tcw/validate.py:178-180`). Only the viewer
discards it.

Downstream, the SPA has exactly one appearance for every branch of that
discarded distinction (`web/client/src/ui/shared-components.tsx:66-73`):

```ts
} else {
    anchor.classList.add("tcw-inert")
    anchor.title = uri
}
```

rendered as gray, struck through, `cursor: not-allowed`
(`web/client/src/style.css:261-265`).

So four different situations collapse into one pixel-identical result:

| Situation                            | Truth                          | What the reader sees         |
| ------------------------------------ | ------------------------------ | ---------------------------- |
| Valid ref, project not on this board | Document correct; board narrow | struck-through gray, raw URI |
| Malformed URI                        | Document broken                | struck-through gray, raw URI |
| Dangling item / unregistered project | Document broken                | struck-through gray, raw URI |
| Store error while resolving          | Neither; a machine fault       | struck-through gray, raw URI |

Two consequences. A reader cannot act — "open the other board" and "fix this
line" are indistinguishable. And the first row is _silent_: it is the expected
state of any cross-node document viewed from the wrong anchor, so it disappears
into the noise. That is how four request documents in the reporter's
orchestrator accumulated downgraded references nobody noticed.

Reproduced on the pre-change tip in two shapes, both valid references to real
items:

- `tcw://W/<descendant-id>/<slug>` in plain `serve` mode. `_hosted_projects()`
  returns the empty set when not aggregating (`tcw/serve/__init__.py:424-427`),
  so the membership test fails.
- An ancestor's item referenced from a child node. The child aggregates its own
  descendants, never its ancestors, so the anchor's project is never in the set.

## Goals

1. `/api/resolve` reports enough about a failure for a client to tell an
   unhosted reference from a broken one, and to name the owning project.
2. An unhosted reference is rendered so a reader notices it in the flow of prose
   without hovering, and can read which project owns it in place.
3. A broken reference tells the reader what is wrong with it, in the words the
   resolver already produces for `tcw validate`.
4. The presentation work changes neither graph reachability nor which projects a
   board hosts. The separately absorbed goal below makes only dangling work-item
   references stop resolving.
5. **A work reference that names no existing item does not resolve.** Absorbed at
   the second rework, on the user's decision. `resolve_tcw_ref` checked existence
   for `T` and `C` and not for `W`, so `tcw://W/<slug>` reported `ok` for a slug
   nobody created — `tcw validate` passed a dangling local reference, and the
   viewer rewrote it into a link that 404s. The failure-reason work above is
   worth less while the resolver lies about which references are broken.
6. **The treatment actually appears on every surface a document is read on.**
   Added at the rework: goals 1-3 were all satisfiable — and were satisfied —
   while a work item's document tab applied no treatment at all, because
   `Markdown`'s resolve pass wrote to DOM that a re-render had already replaced.
   A reader-facing behavior that does not reach the reader has not shipped.

### Applying to the live DOM

`Markdown` resolves links in an effect: it queries the container for
`a[href^="tcw://"]`, posts them to `/api/resolve`, and applies the answers when
the response arrives. It applies them to the anchors it captured **before** the
request — and a render in between can replace that content with byte-identical
HTML, which leaves those nodes detached while the effect does not re-run, because
`[html, resolveLinks]` never changed. Writing to a detached node is silent: no
error, no visible effect, and the one request in the network log looks like proof
that the feature ran.

`work-document-tabs.tsx` triggers this every time. Its `useEffect(…, [item.slug])`
resets state with a fresh `{}`, and a child's effect runs before its parent's — so
the resolve request is always in flight when that re-render lands.

The fix is in `Markdown`, not in that one parent: re-query the container when the
response arrives and apply by `href`. Every call site routes through it, which is
why the same edit restores the capability, taxonomy, and work surfaces at once,
and why fixing the parent's state reset instead would have left the next parent
that re-renders mid-request broken in the same silent way.

A second hole, found by review round 3 and closed here: the re-query alone let a
_stale_ response consume a newer render's anchors. Source A's request is in
flight, source B renders, A answers first, re-queries B's anchors, finds no entry
for B's uris and marks them all unresolved — stripping their hrefs, so B's own
answer then finds nothing left to repair. The effect now sets a `superseded` flag
in its cleanup, which React runs before the next effect, and a superseded response
is dropped. This does not undo the re-query: when the DOM is replaced without the
deps changing, no cleanup runs and the response still applies.

The residual that remains: a replacement landing strictly _after_ the response is
applied would still wipe the treatment, and the effect would not re-run. Not
observed, not reproducible in a test, and not defended against — noted rather than
pre-solved.

## Non-goals

- **`_hosted_projects()` is not touched.** Which projects a board serves is
  correct as it stands; this item is presentation of that decision. Carried
  forward explicitly from the intake.
- **`tcw validate` gains no hostability check.** Settled _no_ in the superseded
  item: hostability is a property of a `serve` invocation, not of stored data,
  so `validate` has no invocation to check against.
- **`resolve_qualified_work_ref` is not changed.** It answers "which store
  addresses this ref", which is what `tcw serve`'s routing wants and what its
  other caller (`_resolve_work`) depends on. The existence check belongs to
  `resolve_tcw_ref`, which answers "does this reference resolve" — the same
  question it already asks of `T` and `C`.
- **The self-qualified-link symptom (GitHub #12)** stays fixed and untested-for
  here; it no longer reproduces and its work-store defect was fixed by
  `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`.
- **No follow-me navigation.** An off-board reference is labeled, not turned
  into a link to another server. There is no second board to link to.
- **`ResolveResult` is not extended.** It already carries everything needed.

## Design

### Sweep

The reported defect is "a computed diagnosis discarded before presentation."
Swept repo-wide: `grep '"ok"' tcw/**/*.py` finds exactly one construction site,
`tcw/serve/__init__.py:971-972`. The only other `resolve_tcw_ref` consumer,
`tcw/validate.py:178`, already surfaces `reason`. Client-side, `resolveLinks` is
the sole consumer of `/api/resolve`
(`work-document-tabs.tsx:148,194`; `content-views.tsx:641,683`), all routing
through the one `Markdown` component. One site, no siblings.

### Resolution response

Keep the `ok` contract exactly as it is: `ok: true` iff the reference resolves
_and_ its destination is hosted. Only the failure branch grows, and it grows a
closed discriminator plus its payload:

```json
{"ok": false, "reason": "unhosted-project", "project": "orchestrator"}
{"ok": false, "reason": "unresolved", "detail": "no such project in this graph: ghost"}
```

- `reason` is one of exactly two values. `"unhosted-project"` when
  `r.ok` is true but `r.project` is not hosted — carrying `project`, never
  empty by construction (a local ref has `project == ""` and is always hosted).
  `"unresolved"` for every `r.ok == false`, carrying `detail` = `r.reason`
  verbatim.
- Prose and code are separate fields on purpose. `reason` is for branching,
  `detail` is for reading; overloading one field is what makes a client sniff
  strings.
- No client outside this repo consumes `/api/resolve` — the SPA is vendored into
  `tcw/serve/dist` and shipped with the server — so the added fields need no
  compatibility shim, and a `{"ok": false}` with no `reason` never occurs.

The presentation response classification does not move into `tcw/refs.py`.
`resolve_tcw_ref` deliberately answers "does this resolve in the registered
graph?" and leaves hostability to the caller
(`tcw/refs.py:88-96`); classifying a _server's_ hosting decision belongs in the
server. Litmus: any store adapter can report "resolved / did not resolve, and
here is why," and any server over it can decide what it hosts — the split is
storage-agnostic, and the new fields carry no filesystem concept.

### Viewer presentation

Three appearances instead of one, all produced in the existing post-render
anchor pass in `Markdown` (`shared-components.tsx:52-75`) — the component keeps
mutating anchors after `marked`; no restructure.

- **Resolvable** — unchanged. `href` rewritten, `data-nav-*` set.
- **Unhosted** — a warning treatment, not the gray one. The anchor gets a class
  distinct from `tcw-inert`, and a sibling badge element carrying the project id
  is inserted immediately after it. Both are visible without interaction; the
  full sentence (`Project <id> is not included in this board`) goes in `title`
  _and_ in an accessible label so it is not hover-only.
- **Broken** — today's `tcw-inert` gray, but `title` carries `detail` instead of
  the raw URI. The URI is still readable in the document source and in the link
  text; the diagnosis was the part the reader could not get.

Both failure appearances must also **stop being clickable**, which today's
`tcw-inert` is not: the delegated handler navigates only on `data-nav-key`
(`web/client/src/ui/app.tsx:891`), so an anchor that keeps its `tcw://` href
hands the click to the browser's protocol handling. `cursor: not-allowed` over a
still-live href is a lie. The href is removed and the address preserved in a data
attribute. (Added after the review, which caught that the item's own title —
"non-link" — was not true of what shipped first.)

The warning treatment must read as a warning in both themes: color from a Radix
scale token (the amber/orange `-11` step), consistent with how `.tcw-inert` and
`.body a[data-nav-key]` already take `--gray-11` / `--accent-11`
(`style.css:257-265`). Strike-through is retained on both failure kinds — the
link is not clickable either way — and the warning color, the badge, and the
glyph carry the distinction. The glyph is decorative CSS generated content, so
the meaning is never glyph-only.

The React source is authoritative and `tcw/serve/dist` is a committed build
artifact (`git ls-files tcw/serve/dist`), so `pnpm build` runs and its output is
committed in the same change; otherwise `tcw serve` keeps serving the old
bundle.

## Acceptance criteria

Server (`tests/test_serve_resolve.py`):

1. With a registered descendant and `include_descendants=False`, resolving
   `tcw://W/<descendant-id>/<slug>` for an item that exists in the descendant
   returns exactly
   `{"ok": false, "reason": "unhosted-project", "project": "<descendant-id>"}`.
2. From a child node whose parent is registered, resolving the parent's item
   returns `reason == "unhosted-project"` with `project` equal to the parent's
   project id, under both `include_descendants` settings.
3. With `include_descendants=True`, the same descendant reference from (1)
   returns `{"ok": true, …}` — unchanged from today.
4. `tcw://garbage` returns `{"ok": false, "reason": "unresolved", "detail":
"malformed tcw:// uri"}`; `tcw://C/nope` returns `reason == "unresolved"` with
   `detail == "no capability: nope"`; `tcw://W/ghost/2026-01-01-x` returns
   `detail == "no such project in this graph: ghost"`.
5. Every failure object carries a `reason` that is one of exactly
   `{"unhosted-project", "unresolved"}`; `project` appears only with the former
   and is non-empty; `detail` appears only with the latter.
6. The existing batch cap and non-loopback-origin rejection tests in
   `tests/test_serve_resolve.py` still pass unmodified. (Corrected after the
   review: there is no non-string-URI test to keep green — non-strings are
   skipped at the loop head and were never covered. Not added here; the skip is
   untouched by this change.)
7. `tcw validate` output for a node containing an unhosted-but-valid reference
   is byte-identical before and after the change (an unhosted reference is not a
   validation problem).

Client (`web/client/src/ui/shared-components.test.tsx`, new coverage for
`Markdown`):

8. Given a stubbed `/api/resolve` returning `unhosted-project` with
   `project: "orchestrator"`, the rendered anchor carries the unhosted class,
   does **not** carry `tcw-inert`, has no `data-nav-key`, and is followed by an
   element whose text content is exactly `orchestrator`.
9. The sentence `Project orchestrator is not included in this board` is
   reachable two ways for that anchor: as the link's accessible description
   (`aria-describedby` resolving to an element that carries the sentence), and as
   text present in the rendered container (visually-hidden counts) — so the
   meaning survives both a screen reader and a reader who never hovers.
   (Corrected after review round 2: this said `getByRole("link", …)`, which an
   unopenable reference deliberately no longer satisfies — removing the `href`
   removes the implicit link role. A criterion that requires the thing the change
   set out to remove would have blessed the defect it was written to prevent.)
10. Given `unresolved` with `detail: "no such work item: x"`, the anchor carries
    `tcw-inert`, carries no badge sibling, and its `title` is
    `no such work item: x`.
11. Given `ok: true`, the anchor is rewritten to the in-app path with
    `data-nav-axis`/`data-nav-key` and carries neither failure class.

Work-item document tab (`web/client/src/ui/work-document-tabs.test.tsx`, added
at the rework — the `Markdown` tests render the component directly and stay green
while this surface is dead, which is how it went unnoticed):

16. Mounting `WorkDocumentTabs` with an item whose body holds a `tcw://`
    reference, with `/api/resolve` stubbed to answer `unhosted-project`, ends
    with that anchor carrying `tcw-unhosted`. This test must fail against the
    pre-rework `Markdown`.
17. In the running app, a work item's Initial Request tab shows all four
    appearances, and a resolvable reference navigates in-app from that tab —
    the `data-nav-key` rewrite was equally dead there before.

Work-reference existence (`tests/test_refs.py`, added at the second rework):

18. `tcw://W/<slug>` for a slug no item carries returns `ok: false` with
    `no such work item: <slug>`, and the same holds for
    `tcw://W/<registered-project>/<slug>` — the defect covers both spellings, not
    only the bare one.
19. `tcw validate` reports a dangling bare work reference as a problem. It did
    not before, which was the defect's headline consequence.
20. `tcw validate` on this repo still exits `0` — the stricter resolver finds no
    dangling reference in the tree it now checks properly.

Whole tree:

12. `pytest`, `pnpm lint`, `pnpm test` pass, and `pnpm exec tsc --noEmit` is
    clean. (Corrected after the review: `pnpm typecheck` runs `prettify:check`
    first, and that is **red on `main`** for 104 pre-existing files, so it cannot
    be a gate for this change. The gate is instead: the files this change touches
    pass `pnpm prettier --check`, and the 104-file baseline count does not grow.)
13. `pnpm check:build` reports the committed `tcw/serve/dist` matches a fresh
    build of the source in the same commit.
14. No committed e2e screenshot moves. (Corrected after the review: the
    original wording required the whole suite to pass, and it does **not** on
    `main` — `parity.spec.ts:332` times out at line 392 and six tests then never
    run. Confirmed pre-existing by running the suite against `5ecdb9a`. What this
    change is accountable for is that the seven tests which do run still pass and
    no snapshot changes.)
15. The two capability descriptions retain the true unresolved-target behavior
    and add the off-board distinction, and `tcw capabilities check` exits `0`.

## Risks

- **Surfacing `detail` puts a store exception's `str(e)` in the browser DOM**
  (`tcw/refs.py:131-132`), which for an `OSError` can name an absolute path.
  Weighed and accepted: `tcw serve` binds `127.0.0.1` only, `/api/resolve`
  rejects a non-loopback `Origin` and requires CSRF
  (`tests/test_serve_resolve.py:165-172`), and `tcw validate` already prints the
  identical string to the same person's terminal on the same machine. The
  requester chose the store's own message over a generic one.

    **Corrected after the review:** the first version of this argument claimed it
    "discloses nothing to anyone who could not already read the store." That is not
    established. Loopback binding and the Origin/CSRF checks are network and CSRF
    controls, not caller authentication — any local process that can reach the port
    can query the server, including one running as an account with no read access
    to the store. The accepted threat model is therefore narrower and is stated as
    such: **anything the served node can read is readable by any local process that
    can reach the port, and a store exception's message is part of that.** That is
    already true of every other route's payload; this change does not widen it. The
    values are inserted via `title`/`textContent`, never into
    `dangerouslySetInnerHTML`, so there is no markup-injection path.

- **A louder treatment is louder for the common case too.** A cross-node
  document read from the wrong anchor may now carry many warning markers. That
  is the requested behavior — the failure being fixed is that it was quiet — but
  if it proves noisy in practice, the dial is the CSS, not the response shape.
- **The badge is inserted DOM, not React.** It lives in `dangerouslySetInnerHTML`
  content that React does not own, matching how `tcw-inert` is applied today.
  The live query selects only anchors whose `tcw://` href remains, and every
  treated anchor loses that href, so the same anchor cannot be treated twice.
  No authored DOM marker is trusted as an ownership guard.
- **Forgetting the bundle rebuild ships nothing.** The Python package serves
  `tcw/serve/dist`; a source-only change is invisible at runtime and passes every
  Python test. `pnpm check:build` is the guard (criterion 13).

## Notes

- The intake carried the superseded item's sketch as "a starting point rather
  than a settled design." This spec keeps its `unhosted-project` /
  `project: <id>` shape and its inert-plus-badge idea, and goes past it in two
  places the requester asked for at `request`: a warning treatment rather than a
  quiet badge, and a second failure class so a broken reference reads
  differently from an off-board one.
- Line citations were re-checked against the tree at spec time; the only
  interleaving change in this repo since the intake was written is the v1.0.2
  release cut, which touched no file cited here.
