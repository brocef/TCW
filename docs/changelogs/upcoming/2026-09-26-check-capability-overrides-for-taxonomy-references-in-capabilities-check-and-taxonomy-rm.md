## Fixed

- `tcw capabilities check` now checks the references a local override sets:
  `_ref_problems` runs over each override's fields (minus structural keys and
  `null` clears, via the new `FsCapabilitiesStore._override_fields` /
  `_set_fields`), reported under the override folder's path. Before, only
  `list_all(local_only=True)` was checked, and `_local_paths` excludes overrides.
- `tcw taxonomy rm`'s capability guard (`FsTaxonomyStore._capability_referrers`)
  also refuses a term an override's `Subject` or `Feature` names, reporting it as
  `capability override <path> (<field>)`.
