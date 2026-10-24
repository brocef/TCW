## Added

- `tcw/store/base.py` `combine`, `Declaration`, `Combined` (`chain`, `owner`,
  `overrides`, `fields`, `description`, `declared_by`, `unused`,
  `unreadable`), `Unused`, `missing_parts` and `clash_warning`: one object
  combined over its chain, key by key, the nearest non-blank description
  winning (Design 2). (TCW-112)
- The tree stores' `own_paths`, `has_own`, `declaration`, `chain`,
  `inherited_at`, `view_warnings` and `removal_target`; capabilities also
  `override_target`. `tcw/locate.py` `Locator.exists` (existence asked of the
  owner's own store alone) and `Locator.store`. (TCW-112)
- `Term.overrides` and `Capability.overrides`, and `partial` on both; the
  `overrides` and `partial` record keys in the CLI's JSON and the web app's
  records, after `parent`; `show` prints `overrides:` or `partial: inherited
content could not be read`. (TCW-112)
- `CapabilityDetail.declared_description`, and `declaredDescription` in the
  web app's capability answers (`GET`, `POST`, `PATCH`). (TCW-112)
- `InheritedUnavailable`'s `"store"` reason and `detail`, and
  `ProjectRegistry.unavailable(..., store_message=)`, for a source whose store
  cannot be opened. The web app answers any `InheritedUnavailable` with `503`
  and `{"code": "inherited-unavailable"}`. (TCW-112)
- `tcw validate` findings: an own object that overrides nothing and is
  incomplete (Design 6.1); two unrelated declarers at one path, as a warning
  (Design 2.5, 6.3); an `overrides:` key in a state file (Design 6.4); one
  `unresolved` finding per axis whose inherited content could not be read
  (Design 6.5). `list` and `search` print the clash warnings on standard
  error. (TCW-112)

## Changed

- Inheritance comes from the parent links: the sources of an axis are
  `source_entries(axis)` in load order. `get_local` and `get_view` read the
  combined view; a full identifier names its owner's own object as its owner
  sees it, through `Locator.read` and `find_tree`, whether or not the active
  project inherits from that owner. (TCW-112)
- `find_tree_writable(store, text, *, removing)` returns the active project's
  own full identifier for the write, from `removal_target` or
  `override_target`. (TCW-112)
- `tcw capabilities set` on an inherited capability writes the project's own
  object at the same id-path holding only the fields given (no name, no id,
  no `description.md`); a cleared field is written as `null` on every own
  object: `--field K=` writes `K: null` where it wrote an empty string, and
  `--parent ''` writes `parent: null`. `reset` takes the id-path,
  the project's own full identifier or the overridden object's.
  `rm` removes an override and prints `<id-path> now shows <full id>`.
  `tcw capabilities add` at an inherited path is refused; `tcw taxonomy add`
  there writes an override of what differs and says what it overrides;
  `--kind` has no default there. (TCW-112)
- `tcw validate` reports a capability's field findings (an unknown or retired
  field, a value a field cannot take, `Partial` without `Gaps`) at its state
  file, `docs/capabilities/<path>/tcw-capability.yaml`, where it named the
  folder. (TCW-112)
- `update_capability` writes a given body, an empty one included, as the
  declared description; the web editor's body field starts from
  `declaredDescription`, and notes when the page's body holds more. A term
  override edited in the web app is written in place. (TCW-112)
- The records gate routes every entry to its owner's own ledger and reads the
  owner's combined `Status`; `removed` asks only whether the owner has an
  object of its own; an owner whose view cannot be built is unchecked. Drift
  builds the view first and treats an override that sets no `Status` as
  never ruled on. (TCW-112)
- `tcw validate` checks each own object's fields as the project sees them and
  its references as it declares them; row k applies to capabilities; a
  nested override is not a misplaced folder; the pre-2.5.0 store file's
  message names `parents:`. A scoped check reads only its own object.
  `resolve_address` asks existence only. (TCW-112)
- The view is built once per store and only when something needs inherited
  content; a project whose own configuration names no parent asks the
  registry nothing. (TCW-112)

## Fixed

- A web body edit of a capability with attached documents no longer writes
  their text into its `description.md`. (TCW-112)

## Removed

- `taxonomy.extends` and `capabilities.extends` (refused in the active
  project's own file, ignored in another project's, and gone from the table
  of known keys); `tcw taxonomy extends add|rm` and `tcw capabilities extends
add|rm`; the stores' `extends_add`, `extends_remove`, `get_inherited`,
  `get_by_id`; `_extends_ids`, `_FederationWalk`, `_FederationCycles`,
  `_extended_component_stores`, `_persist_extends`, `_extends_label`,
  `_apply_override`, the override index and field helpers,
  `_status_is_local`, `_mint_cap_id`, `Capability.id` and `AmbiguousRef`.
  (TCW-112)
- The federation cycle and alias collision checks, the `overrides:` pointer
  checks, "missing Status" as a message of its own, and the records gate's
  `INHERITED` outcome. (TCW-112)

## Internal

- Test fixtures no longer write `extends`, the override pointer or `cap-`
  ids; `write_cap(..., complete=False)` writes an override as 4.0 keeps one.
  A property test of `combine`, and a static guard,
  `tests/test_no_3x_inheritance.py`, that keeps the removed code and fixture
  forms out. (TCW-112)
