# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

<changes starting-hash="4777fac" ending-hash="956951a">

### Added

- Work-item **tags**: a node-scoped registered tag set stored under `work.tags`
  in the node-root `tcw-config.yaml`, plus a multi-value `tags` field on items.
  - `WorkItem.tags: list[str]` and `normalize_tag()` (slugify + non-empty guard)
    in `tcw/store/base.py`; new `WorkStore` ABC methods `registered_tags()`,
    `register_tags()`, `unregister_tags()`, and `check()`.
  - `FsWorkStore` (`tcw/store/fs.py`): `_config()`/`registered_tags`/`register_tags`/
    `unregister_tags`/`_validate_tags`/`check`; `create_work`/`update_work` gain a
    `tags` kwarg and reject unregistered tags (fail closed); `_item_from_dir` reads
    `tags` (omitted from `state.yaml` when empty).
  - CLI (`tcw/work/cli.py`): `tcw work tags {list,add,rm}` subcommand group;
    `--tag` on `new`, `--tag`/`--untag` on `edit`, `--tag` filter (match-any) on
    `list`; tags shown in `show` and board rows.
  - Web (`tcw/serve/__init__.py`): `GET /api/work/tags`; POST create + PATCH
    allowlist accept `tags` (unregistered → 422). `app.js`/`style.css`: registered-
    set checkbox multi-select in the work create/edit editors, tag display on the
    detail view and list rows.

### Changed

- `tcw validate` runs the work component's `check()` (whole-node and paths under
  `docs/work`), reporting items carrying a tag no longer in the registry.

</changes>

<changes starting-hash="047e274" ending-hash="27d7179">

### Added

- Web viewer **multi-select category filter** (`tcw/serve/static/app.js`,
  `style.css`): a reusable native `<details>` facet dropdown
  (`renderFacetDropdown`) driving `state.kindFilter` (taxonomy Kind:
  Feature/Vocabulary) and `state.tagFilter` (work Tags, from
  `GET /api/work/tags`; multiple selected = OR/match-any). `itemVisible()` and the
  `renderList()` prune gate extended to honor the facets, composing with the text
  filter and status toggles. `renderStatusFilters()` generalized to
  `renderFilterControls()` (status toggles + Tags for work; Kind for taxonomy;
  none for capabilities); the `#status-filters` row now shows for taxonomy too.

### Changed

- Web viewer layout (`tcw/serve/static/style.css`): the object-list column scrolls
  independently — `.shell` is viewport-bounded (`height` + `overflow: hidden`),
  `.list-pane` is a flex column with a fixed head, `.list` and `.detail-pane` get
  their own `overflow-y: auto`; the mobile breakpoint reverts to natural page
  scroll. A long tree no longer grows the whole page.

</changes>
