# Interactive local web editor for TCW objects

## Product changes

Build on the recently completed `tcw serve` read-only web viewer and make the
local web app interactive.

Users should be able to edit every field and content surface of existing TCW
objects from the browser, including YAML-backed metadata files such as
`state.yaml`, taxonomy `meta.yaml`, capability inline metadata, and work
sidecars such as `capabilities.yaml`.

Users should also be able to create new TCW objects from the browser, including
work items, taxonomy vocabulary/feature entries, and capability entries.

The main lifecycle files (`initial-request.md`, `spec.md`, `plan.md`,
`outcome.md`, and `refined-outcome.md`) are required to be Markdown files, so
the browser should provide a rich Markdown editing experience. MDX Editor is the
preferred reference candidate for that interaction, subject to the implementation
constraints of packaging TCW as a Python CLI/plugin.

## Technical changes

- Extend the `tcw serve` JSON API from read-only GET routes to write-capable
  create/update routes.
- Preserve TCW's storage abstraction: write routes should call abstract store
  operations, not manipulate `docs/` paths directly in the web layer.
- Add or extend store-interface methods where the operation has a clear abstract
  analog: create item, update bounded fields, update body/content, update named
  attachments, and update lifecycle artifacts.
- Keep filesystem-specific YAML/Markdown persistence inside filesystem adapters.
- Decide whether to introduce a frontend build step for MDX Editor or to vendor
  compiled assets in a way that still works for plugin/pip installs.

## Meta changes

- Declare the new web editing capability as Missing while this work is planned.
- Link the capability to the `local-web-app` taxonomy feature.
- Update public docs, changelog/release notes, and the driving skills when the
  write API and web UI land.

