# Plan: show the server's message for a web save refused for a reason other than a stale revision

## Tasks

1. **Server marker.** Tests first in `tests/test_serve_write.py`: assert
   `code == "stale-revision"` in `test_update_stale_revision_409` and in an
   artifact PUT stale test; assert no `code` on the generated-sidecar 409
   (`:737`). Then `_map_store_error` in `tcw/serve/__init__.py`. Proof: red → green.
2. **Client.** Add `isStaleWrite` to `web/client/src/model/api.ts` with a test
   file `web/client/src/model/api.test.ts` (criterion 2, red first against a stub
   returning `status === 409`); use it at both save branches in
   `web/client/src/ui/app.tsx`. Rebuild the bundled app (`pnpm build`) so
   `tcw/serve/dist` matches, as the repo's build check requires.
   Proof: vitest, typecheck, lint, `pnpm check:build`.
3. **End to end.** Run `pnpm test:e2e` (criterion 3).

## Documentation Sync

- `docs/changelogs/upcoming.md` [Any-Code-Change] — Fixed + the new `code` field.
- `docs/release-notes/upcoming.md` [Public-API] — one plain line.
- README/guides/skills/configure: expected not to fire; re-checked on the diff.

## Verification

Hands-on in Chrome (the Claude profile) against `tcw serve` from the worktree:
cause a real stale save and see the banner; for a non-stale 409 the UI has no
control, so check it by sending the PUT from the page's console with the app's
own code path unavailable — rely on the unit test and state that limit in
`outcome.md`.
