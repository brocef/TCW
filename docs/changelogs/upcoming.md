# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- `init` (`tcw work init`, `tcw init`) no longer writes back a `work.path` it read
  from `tcw-config.yaml` when no path was given: `./store` now stays `./store`
  instead of becoming `store`, and `~/store` is no longer expanded into an
  absolute home-directory path in a committed file. A `~name` naming no user (in
  `work.path` or `--path`) is reported as `tcw init: …` instead of a traceback.
- The web app opened its "Stale write detected" banner for every 409 from a save,
  dropping the server's message. A stale-revision refusal now carries
  `"code": "stale-revision"` in its JSON body (`_map_store_error`), and the
  client (`isStaleWrite` in `web/client/src/model/api.ts`) opens the banner only
  for that; any other refusal — a write to a generated sidecar, for one — shows
  the server's message. Status codes are unchanged.
