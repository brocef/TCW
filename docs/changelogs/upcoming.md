# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- `taxonomy.path` and `capabilities.path` in `tcw-config.yaml`, with
  `tcw init --taxonomy-path` and `--capabilities-path` to scaffold at them.
  `FsTreeStore.open` read no configuration at all before this: it was the single
  expression `cls(node_root / "docs" / cls.COMPONENT)`.
- `taxonomy.repository` and `capabilities.repository`, resolved and provisioned
  by the mechanism `work.repository` already used. `declared_repository` was
  written component-generic in the previous release and needed no change.
- `resolve_store(store_cls, node_root)` — the four-rule resolution ladder,
  extracted from `FsWorkStore.open` and shared by every component. The two things
  that differ per component are the `_local_root` and `_open_at` hooks on the
  store class; `COMPONENT` names the config section.
- `STORE_CLASSES`, a component → store-class mapping, so `find_node` and
  `run_provision` name one lookup instead of each growing its own `if component
  ==` ladder.

### Changed

- `PROVISION_COMPONENTS` widens from `("work",)` to every component. It was
  narrowed deliberately while only the work-store layout existed; the adapters
  arrive in the same change, never after the values that advertise them.
- `_is_store_layout` takes the component and answers per component. A work store
  is its six status folders; a tree store is an existing directory, which is the
  strongest honest answer — `init` scaffolds a tree component as a bare folder,
  `CONFIG_NAME` is optional and commonly absent, and the only file reliably left
  is a `.gitkeep`. The weaker guarantee is stated in the capability bodies.
- `FsTreeStore` splits `node_root` from a new `store_git_root`, the same split
  `FsWorkStore` has carried since `work.path` existed. `node_root` is the node,
  which federation resolves `extends` against; `store_git_root` is the repository
  a write lands in. They diverge as soon as a tree store leaves its node's
  repository, and conflating them broke `extends` resolution for a provisioned
  tree.
- `init` takes a `paths` mapping beside `work_path`, which keeps its name and
  position — `tcw init --work-path` and `tcw work init --path` both spell it that
  way, and every existing caller passes it positionally.
- `_run_check` guards the store open for all three components. Only `work` was
  guarded, so a declared-but-unprovisioned tree raised past `tcw validate` and
  ended the run with one component's problem instead of listing it beside the
  others.

### Fixed

- `find_node` answered "does this node have this component?" by looking for a
  literal `docs/<component>/` folder. That is exactly wrong for the case the
  feature exists for: a checkout that cloned only the code repository has no such
  folder, so the declaration went unread and `tcw taxonomy list` reported the
  project as having no taxonomy. It now asks the resolved store.
- `run_provision` called `FsWorkStore.open` from inside its loop over components
  to decide whether a local store already satisfied a declaration. Correct only
  while the component tuple held one value; with more, a taxonomy declaration was
  measured against whether the *work* store resolved, and would be cloned because
  it did not.
- A provisioning refusal for a path that names nothing in the repository said
  `missing: inbox, backlog, …`, reading as an incomplete store when the whole
  directory is absent. It now says so, and the enumeration is kept for the
  present-but-incomplete case it describes.
