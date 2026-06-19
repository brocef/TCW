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

<changes starting-hash="a9cea6f" ending-hash="84f1545">

### Changed
- Work status vocabulary reduced from five to four: `blocked` folder dropped;
  `blocked_by` relations now live in `state.yaml` as a list of dicts, readable
  via `WorkItem.blocked_by` (renamed from `blocked_on`).
- `tcw work block` and `tcw work unblock` subcommands removed; `block`/`unblock`
  methods removed from `WorkStore`; `link` method removed from `FsWorkStore`.
- `docs/work/` init no longer creates a `blocked/` folder.

</changes>

<changes starting-hash="b963c75">

### Added
- `WorkStore.add_blocker(slug, ref)` / `remove_blocker(slug, ref)` — concrete
  relation operations in the core, cycle- and self-block-guarded; adding an
  already-present entry is idempotent.
- `WorkStore.unresolved_blockers(item)` — returns labels of blockers that still
  block an item; a slug that no longer resolves counts as resolved.
- `WorkStore.board(status=None)` — `query()` wrapped with topological ordering.
- `topo_order(items)` — module-level pure function; both-endpoints-in-set
  constraint, stable tie-breaking by input order, residual-cycle fallback.
- `WorkStore.start` / `complete` — blocker gating via `unresolved_blockers`;
  both accept a `force: bool` parameter to override.
- `tcw work edit <slug> [--blocked-by <refs>] [--blocks <refs>] [--unblocked-by
  <refs>]` — CLI subcommand to add/remove blocking relations. `--blocks`
  targets are validated against the store (must exist).
- `tcw work new --blocked-by <comma-separated refs>` — blockers attachable at
  item-creation time. The item is always created and its slug printed, but the
  command exits non-zero if a blocker fails to attach (e.g. an ambiguous ref).
- `tcw work start --force` and `tcw work complete --force` — skip the
  unresolved-blocker gate (blocker check runs before the DoD checklist).
- `tcw work list` — topological ordering via `board()`, `blocked-by: …`
  annotation for items with unresolved blockers.
- `_split(val)` helper in `tcw/work/cli.py` for comma-splitting flag values
  with empty-token elision.

</changes>
