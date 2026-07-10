# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## New Features

- **Reference any TCW object with a `tcw://` link.** In an object's body prose you
  can now link to a Taxonomy term, Capability, or Work item with a
  `tcw://[<namespace>/]<axis>/<ref>` link (axis = `T`/`C`/`W`). They're ordinary
  Markdown links, and they can point at objects in another project via an
  `extends` alias (taxonomy/capabilities) or a descendant node path (work).

- **`tcw validate`** — one command that checks a whole node (or a single file or
  folder) in one pass: malformed YAML, `tcw://` links that don't resolve, and the
  problems each component's own check reports. Prints `validate OK` when clean, or
  a grouped list of problems otherwise. Examples of the scheme inside code blocks
  are ignored, so docs that teach it don't fail their own check.

## Changes

- **The local web viewer follows `tcw://` links.** A `tcw://` reference in a
  rendered body is now a clickable in-app link — clicking it navigates to the
  target object (and browser Back returns). A link to something the viewer isn't
  hosting (a foreign project, or a dangling reference) renders inert.
