## Added

- `connected-projects.upstream`: a one-way, read-only connection declared only
  by the reader. `FsProjectRegistry` loads an upstream's config without
  following its `parent`, `children` or `upstream` edges, and quietens its
  connection problems; a config reached both as upstream and as family is loaded
  fully. Absent upstreams are unreachable, as absent children are.
- `ProjectRegistry.read_only_reason(project_id, from_id=None)`: why a project may
  not be written from a node — writable only when reached through parent and
  children edges alone, as each visited project declares them. Also
  `declared_upstream_ids()` and `warnings()`, with non-abstract defaults.
- `qualified_work_ref_read_only` and `resolve_qualified_work_ref_for_write` in
  `tcw/store/fs.py`. Every CLI verb that changes an item or runs its project's
  scripts resolves through the write form; `show`, `path` and `lifecycle` keep
  the reading form.
- `tcw serve` (which always serves descendants) answers 403 (`code: read-only-project`) on
  every changing route for an upstream item; reads are unchanged.
- `tcw work nodes` prints an `upstream (read-only):` section — each upstream
  declared by the node or an ancestor, its declarer and location — only when
  there is one.
- Graph problems: a project declared as its own upstream; an upstream also
  reachable as family from its declarer. A `duplicate project id` names the
  upstream declarers involved.
- `tcw validate` prints registry warnings as `warning: …`.

## Changed

- Reciprocity: a parent claim answered by a loaded config declaring the node
  upstream is a warning, not a `nonreciprocal connection` problem, so moving a
  child to upstream blocks neither repository.
- `declared_connected_projects` reads `upstream` and returns each entry's
  relation; `tcw provision` obtains an upstream but does not follow its own
  declarations, and skips upstream projects when walking the graph.
- `tcw work delegate` refuses an upstream with the read-only reason.
- `checkout_of` searches `upstream` entries.
- An incomplete `work.tracker` block in a project with no parent gets a
  "no parent to inherit work.tracker settings from" line beside its
  `required` problems.
