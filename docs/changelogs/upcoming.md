# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- `init` (`tcw work init`, `tcw init`) no longer writes back a `work.path` it read
  from `tcw-config.yaml` when no path was given: `./store` now stays `./store`
  instead of becoming `store`, and `~/store` is no longer expanded into an
  absolute home-directory path in a committed file. A `~name` naming no user (in
  `work.path` or `--path`) is reported as `tcw init: …` instead of a traceback.

### Fixed

- `tcw work start <slug> --take-over` recovers an interrupted claim again. `_start`
  read the item with `get` for the `pre` hook before reaching the store, and
  `get` raises for an item left in `.claiming/`, so the documented remedy
  printed the same error. New `WorkStore.interrupted_claims()` (default `[]`;
  `FsWorkStore` reads `.claiming/<slug>-<hex>`, reporting each item as it was,
  status `backlog`) supplies the item for the hook, `before` and `previous`.
  Under strict tracker mode a recovery runs the same ticket claim as a start,
  with the binding rebuilt from the claimed item (`_recovered_binding`;
  `binding_refusal` gained `binding=`), since no store read reaches a claim.
- The web app can recover one: `GET /api/work/interrupted-claims` (every node
  the board shows, slugs qualified the same way), and the start action's
  `recover: true`, which claims for the server's identity (`_local_owner`)
  through the store's new `start(..., recover=True)`: a take-over that refuses
  any item settled in a status, decided against the same read it acts on, so a
  claim published meanwhile is never taken from its owner. The board shows a
  notice with a Recover button. `_strict_refuses` reads an interrupted claim
  instead of raising on it.
