# Aggregate descendant nodes' taxonomy and capabilities in tcw serve

`tcw serve` aggregates every descendant node's **work board** automatically, but
serves the Taxonomy and Capabilities axes from the anchor node alone. On a
routing node that keeps a board but no ledgers of its own, the web app therefore
opens with a populated Work tab and two silently empty ones, even though every
descendant beneath it has a full `docs/taxonomy/` and `docs/capabilities/`.

Both axes should aggregate the same way the board does, so that serving a
repository root shows the whole workspace on all three axes rather than one.

## Origin

Reported in chat on 2026-09-19. The user ran `tcw serve` from
`~/Projects/proposit-orchestration/proposit-app` — the `proposit-app-repo` node
— and found taxonomy and capabilities not populating while the board was fine.

Reproduced against that tree with the current checkout:

```
taxonomy      ok, entries: 0
capabilities  ok, entries: 0
descendants:  proposit-app/packages/shared
              proposit-app/apps/server
              proposit-app/apps/mobile
```

`proposit-app-repo` configures a work store but no taxonomy or capabilities
store; its own `docs/` holds only `lifecycle/`. All three descendants keep
populated ledgers at the default locations.

The cause is in `tcw/serve/__init__.py`:

- `_board()` (line 474) walks `[anchor] + descendant_nodes(anchor)` and qualifies
  each descendant slug as `<project-id>/<slug>`. That is why Work populates.
- `_stores()` (line 442) opens `FsTaxonomyStore` and `FsCapabilitiesStore` on
  `self.server.node_root` only. The `GET /api/taxonomy` (line 751) and
  `GET /api/capabilities` (line 776) routes call `list_all()` on those, with no
  descendant walk and no qualified refs.

The web-viewer guide is accurate as written — it scopes the claim to "every
descendant node's **board**" (`docs/guide/web-viewer.md:38-42`) — so this is a
parity gap rather than code contradicting its documentation. It still reads as a
defect to someone using the app, because nothing in the UI distinguishes "this
node has no ledger" from "this axis is not aggregated".

## What a fix has to decide

- `descendant_nodes()` filters on `_has_work_store()` (`tcw/store/fs.py:345`), so
  reusing it for the other two axes would skip any descendant that keeps a ledger
  but no board. Each axis needs its own node walk against its own store.
- Descendant entries need qualified refs so the detail routes
  (`GET /api/taxonomy/<ref>`, `GET /api/capabilities/<ref>`), the `tcw://`
  reference resolver, `_hosted_projects()`, and every write route know which
  node they are addressing. The board already has this shape to copy.
- Write routes (`POST`/`PATCH` on both axes) must either route to the owning
  node or refuse a descendant ref outright — silently writing a descendant's
  term into the anchor's store would be worse than the current gap.
- Taxonomy and capabilities already support inheritance through `extends`. How an
  aggregated view relates to an inherited one needs settling, so the same term
  does not appear twice under two different refs.

## References

- `docs/guide/web-viewer.md:38-42` — the existing, board-only aggregation claim;
  it needs updating with whatever this item lands.
- `2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile`
  — related, not blocking. Same class of problem (a node walk filtered on the
  presence of a work store), in `delegate` and `reconcile` rather than `serve`.
  Whatever helper that item adds for descending past a storeless node may be
  reusable here, and both items should end up consistent about what a routing
  node is.
- `2026-07-08-web-viewer-resizable-panes-url-routing-descendant-nodes-and-taxonomy-inheritance-fix`
  (completed, commit `6c015d0e`) — where board aggregation was added, and the
  pattern to follow for qualified refs.
