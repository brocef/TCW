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
