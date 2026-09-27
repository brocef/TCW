# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- The web app opened its "Stale write detected" banner for every 409 from a save,
  dropping the server's message. A stale-revision refusal now carries
  `"code": "stale-revision"` in its JSON body (`_map_store_error`), and the
  client (`isStaleWrite` in `web/client/src/model/api.ts`) opens the banner only
  for that; any other refusal — a write to a generated sidecar, for one — shows
  the server's message. Status codes are unchanged.
