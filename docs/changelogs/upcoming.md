# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed (`a797cfc`..)

- `skills/documentation-sync/scripts/unpushed-version.sh` — the `UNKNOWN` message
  now states that `git fetch` is not a workaround, and the branch-containment
  comment says the same. Verified empirically: two repos identical but for
  whether the tag was pushed have byte-identical local refs after
  `git fetch --all --tags`, because fetched tags share the `refs/tags/`
  namespace with locally-created ones and git keeps no per-remote tag-tracking
  refs. `ls-remote` is therefore irreplaceable, and an agent that "fixes"
  `UNKNOWN` by fetching would conclude wrongly.
- `skills/documentation-sync/references/cut-version.md` — same caveat stated at
  the point of use.
