# Implement — round 1

## What was done, by plan step

1. Tests first: a `path tree by parent` block in
   `web/client/src/model/tree.test.ts`; 4 of its 7 tests failed before the
   change (the cycle, self-parent and path-tree-unchanged tests already
   passed on the old builder, which ignores `parent`).
2. `web/client/src/model/tree.ts`: `buildPathTree` takes `parentKeyOf`,
   makes label nodes for an absent parent, and breaks parent cycles;
   `pathTreeAncestors` added.
3. `types.ts` (`parent` on both record types), `route-utils.ts`
   (`parentItemKey`, `buildRecordTree`), `app.tsx` (tree memo and
   `navigateTo` use them).
4. `app.test.tsx`: one test per axis. Mutation-checked: with
   `buildRecordTree` reverted to path-only placement both go red
   ("expected '1' to be '3'"), green once restored.
5. Bundle rebuilt into `tcw/serve/dist/client` and staged;
   `pnpm check:build` exits 0.
6. Documentation: `docs/capabilities/web/description.md` (the declared
   `changed:` capability), `docs/guide/web-viewer.md`, and the item's
   release-notes and changelog entries.

## Test results (run in this session)

- `pnpm test`: 17 files, 256 tests passed. `tsc --noEmit` exit 0.
  `pnpm lint` clean. Prettier clean on every changed file.
- `pnpm typecheck` as a whole fails on 1938 files unrelated to this change
  (leftover agent worktrees under `.claude/worktrees/` and local files); the
  same count fails with this change stashed.
- Browser check (Claude Chrome profile, fixture projects `core` and `app`):
  under scope up, `Refund` sits under `core.taxonomy › Billing`; under scope
  own, under labels `core.taxonomy › billing`; `Receipt` (`--flat`) under
  `Invoice`; `Refund a bill` under `core.capabilities › Bill customers`.
  Opening `/taxonomy/refund` with `core.taxonomy` collapsed expands it and
  selects the row.
- Bare `pytest` and `tcw validate`: **not yet confirmed** — started, still
  running when this round was written.

## What the plan or spec got wrong

- The plan put `buildRecordTree` nowhere; it went into `route-utils.ts` so
  `navigateTo` and the tree memo share it.
- `pnpm check:build` compares against the git index, so the rebuilt bundle
  must be staged before it passes; the plan did not say so.

## Records changed

- `tcw.capabilities/web` description.

## Rejections answered

None (first round).
