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
