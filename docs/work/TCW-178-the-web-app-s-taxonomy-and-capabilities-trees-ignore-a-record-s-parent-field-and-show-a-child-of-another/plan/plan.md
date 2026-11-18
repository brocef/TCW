# Plan — The web app's taxonomy and capabilities trees ignore a record's parent field

## Steps

1. **Tests first** — `web/client/src/model/tree.test.ts`: add a `path tree
   by parent` block covering spec criteria 1–7 (listed parent of another
   project; absent parent becomes labels; local `--flat` child; unchanged
   tree with no parent or a parent equal to the folder parent; a two-record
   cycle; invalid parent text ignored; `pathTreeAncestors`). Done when
   `pnpm test` shows exactly these new tests failing.

2. **Tree model** — `web/client/src/model/tree.ts`:
   - `buildPathTree(items, keyOf, parentKeyOf?)`: build nodes keyed by path
     as today, link each node explicitly to its tree parent (declared parent
     when `parentKeyOf` gives a key other than its own, creating
     placeholders along that key's segments; otherwise its folder parent),
     then the reachability pass that relinks nodes caught in a cycle to their
     folder parent until every node is reachable from a root.
   - `pathTreeAncestors(nodes, path)`: the paths above the node with that
     path, outermost first, or `[]`.
   - `parseFullId` check for the parent text lives in the caller's
     `parentKeyOf` (step 3), so `tree.ts` stays generic over keys.
   Done when all `tree.test.ts` tests pass, existing ones unchanged.

3. **Types and call site** — `web/client/src/model/types.ts`: `TaxonomyItem.parent?: string | null`,
   `CapabilityItem.parent?: string | null`. `web/client/src/ui/route-utils.ts`:
   add `parentKey(item, projectId)` returning
   `routeKey(item.parent, projectId)` when `parseFullId(item.parent)` is not
   null, else `null`. `web/client/src/ui/app.tsx`: pass
   `(item) => parentKey(item, projectId)` to `buildPathTree` at the tree
   memo, and in `navigateTo` replace `pathAncestors(key)` with
   `pathTreeAncestors(buildPathTree(data[nextAxis], keyOf, parentOf), key)`.
   Remove `pathAncestors` from `app.tsx`'s imports if unused there (keep
   the function; its tests still exercise it). Done when `pnpm test`,
   `pnpm typecheck` and `pnpm lint` pass.

4. **App test** — `web/client/src/ui/app.test.tsx`: one test that serves a
   taxonomy list holding a term whose parent is another project's absent
   term, and checks the term's row is inside the label rows rather than at
   the top (spec criterion 8, as far as jsdom can check it). Done when it
   passes, and fails with step 3's call-site change reverted.

5. **Rebuild the bundle** — `pnpm build`, which rewrites
   `tcw/serve/dist/client/`; then `pnpm check:build`. Done when the check
   passes and `git status` shows the new bundle files.

6. **Documentation Sync** (one block):
   - `docs/capabilities/web/description.md`: the trees sentence says entries
     nest under their `parent:`, under a label when the parent is not listed
     (the `changed:` capability in `capabilities.yaml`).
   - `docs/guide/web-viewer.md` [Guide-Topic-Change]: the "Taxonomy and
     capabilities" bullet says the same.
   - `docs/release-notes/upcoming/<folder>.md` [Public-API] and
     `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change]: new files.
   - Not firing: README.md (no CLI or install change; it does not describe
     the tree's shape), jira.md, skills (no CLI surface change),
     configure references (no key), use-cases.md (no setup's requirements
     or gaps change).

7. **Full suite** — bare `pytest` (as CI runs it) and `tcw validate`.

## Verification

- Run `tcw serve` against a fixture project with a parent project
  (`python evals/seed_fixture.py --customized` is not two projects, so build
  one in the scratchpad: a parent with a term `billing` and capability
  `billing`, a child naming it as `parent` for one term, one capability, and
  a `--flat` child of its own term) and look at the trees in the Claude
  Chrome profile under scope own and scope up, then open a child's URL
  directly and confirm the rows above it are expanded (spec criterion 8).
