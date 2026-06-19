# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

<changes starting-hash="be5ed6a" ending-hash="fe08e5b">

### Added
- Phase 1 scaffold: `tcw` Python package, `pip install -e .` console entry point,
  top-level CLI (`tcw init | taxonomy | capabilities | work`), and `tcw init` —
  the unified scaffolder for `docs/{taxonomy,capabilities,work}/` trees.
- Phase 2 taxonomy: `tcw taxonomy` (`list/add/show/rm/search/check` + bare-path
  `show`) and `FsTaxonomyStore` over `docs/taxonomy/`, with local-path `extends`
  federation and namespace reference resolution. Runtime dep `PyYAML` added.
- Phase 3 capabilities: `tcw capabilities` (`list/show/add/search/check` + bare-id
  `show`) and `FsCapabilitiesStore` over the bounded `docs/capabilities/` tree —
  markdown capability parsing, the file/folder rule, identifier resolution
  (`namespace/path[state]#heading`), the locked status/field vocabulary, and
  cross-component `Subject`→taxonomy validation in `check`.
- Phase 5 work: `tcw work` (`init/new/list/show/path/start/block/unblock/complete/
  drop`) and `FsWorkStore` — the `docs/work/` filesystem state machine. Stable-id
  (slug) resolution, the legal-transition graph + named operations in the core,
  `git mv` transitions, blocker resolution on `unblock`, and the loose DoD gate.

### Internal
- Phase 4: extracted the shared `FsTreeStore` core from the taxonomy and
  capabilities adapters; both re-expressed on it with no behavior change.

</changes>

<changes starting-hash="a9cea6f">

### Changed
- Work status vocabulary reduced from five to four: `blocked` folder dropped;
  `blocked_by` relations now live in `state.yaml` as a list of dicts, readable
  via `WorkItem.blocked_by` (renamed from `blocked_on`).
- `tcw work block` and `tcw work unblock` subcommands removed; `block`/`unblock`
  methods removed from `WorkStore`; `link` method removed from `FsWorkStore`.
- `docs/work/` init no longer creates a `blocked/` folder.

</changes>

<changes starting-hash="061ecd7">

### Added
- `tcw work edit <slug> [--blocked-by <refs>] [--blocks <refs>] [--unblocked-by
  <refs>]` — new CLI subcommand to add/remove blocking relations. `--blocks`
  targets are validated against the store (must exist); `--blocked-by` and
  `--unblocked-by` follow the same external-ref rules as the store layer.
- `tcw work new --blocked-by <comma-separated refs>` — blockers can now be
  attached at item-creation time.
- `tcw work start --force` — skips the unresolved-blocker gate.
- `tcw work complete --force` — skips the unresolved-blocker gate (blocker check
  is performed before the DoD checklist is printed, so the gate fails fast).
- `tcw work list` — now uses `WorkStore.board()` for topological ordering
  (blockers appear before the items they block) and appends a `blocked-by: …`
  annotation for items with unresolved blockers.
- `_split(val)` helper in `tcw/work/cli.py` for comma-splitting flag values
  with empty-token elision.
- `"edit"` added to `SUBCOMMANDS` in `tcw/work/cli.py`.

</changes>
