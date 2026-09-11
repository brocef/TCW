# Linking and validation

How one TCW object references another, and the single command that checks a
whole project graph.

## `tcw://` links — reference a TCW object

Any object's body prose can point at another TCW object with a `tcw://` link:

```
tcw://[<project-id>/]<axis>/<ref>
```

- `<axis>` is `T` (Taxonomy), `C` (Capabilities), or `W` (Work).
- `<project-id>` (optional) is a registered descendant for `W`, or a project
  explicitly listed by that axis's `extends` for `T`/`C`. Absent = local.
- `<ref>` is the identifier within that axis (taxonomy slug/path, capability
  path, work slug).

```markdown
See [Read a capability](tcw://C/capabilities/read-a-capability) and the
[reference](tcw://T/reference) term, or work item [tcw://W/2026-01-01-x](tcw://W/2026-01-01-x).
```

These are inline Markdown links, so they render as normal links in any viewer and
become **in-app navigation** in `tcw serve`. The viewer distinguishes the two ways
a reference can fail to become a link: one that points at a real object on another
project's board is marked off-board and names that project, while a malformed or
dangling one says what is wrong with it. They're additive — they don't replace
the structured pointers (a capability's `Subject`/`Feature`, a work item's
`blocked_by`). Stored Markdown is never rewritten.

## `tcw validate` — one-pass soundness check

Bare `tcw validate` checks the active TCW project and every registered descendant
project recursively. Use `--no-recurse` to check only the active project, or pass
a path to run a bounded active-project scan (which also disables recursion):

```sh
tcw validate                    # active project + all registered descendants
tcw validate --no-recurse       # active project only
tcw validate docs/capabilities  # one active-project tree only
```

For each selected project it reports malformed YAML (including duplicate keys),
a file TCW writes as a record that is not a mapping, a `tcw://` link that doesn't
resolve, and problems surfaced by each component's own `check` (taxonomy +
capabilities + work). Recursive diagnostics include the
project ID so matching relative paths remain distinguishable. It exits `0` with
`validate OK` only when every selected project is clean; otherwise it prints the
problems and exits `1`. `tcw://` examples inside Markdown code spans are ignored,
so docs that teach the scheme don't fail themselves.

### A record of the wrong shape

A YAML file TCW writes as a record — `state.yaml`, `meta.yaml`,
`graveyard.yaml`, and a store's `config.yaml` — has to be a mapping. One that is
not is reported by name:

```
docs/work/backlog/2026-09-11-login-crash/state.yaml: expected a mapping, found list
```

This is the only place such a file is reported. Reading one deliberately
degrades to empty instead of failing, so that a single damaged item cannot make
the whole board unlistable — which means the item goes on looking healthy
everywhere else until `tcw validate` says otherwise.

Any *other* YAML under the scanned trees may be any shape at all. `dod.yaml` is
a top-level list on purpose, a work item's `capabilities.yaml` is a mapping or a
list depending on which form wrote it, and an attachment parked beside an item is
whatever its author wanted. None of them is held to the mapping rule.
