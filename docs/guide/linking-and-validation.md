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
a `tcw://` link that doesn't resolve, and problems surfaced by each component's
own `check` (taxonomy + capabilities + work). Recursive diagnostics include the
project ID so matching relative paths remain distinguishable. It exits `0` with
`validate OK` only when every selected project is clean; otherwise it prints the
problems and exits `1`. `tcw://` examples inside Markdown code spans are ignored,
so docs that teach the scheme don't fail themselves.
