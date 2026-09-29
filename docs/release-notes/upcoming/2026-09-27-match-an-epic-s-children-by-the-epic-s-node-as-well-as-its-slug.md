## Fixed

- **Epics in different projects no longer mix up their tasks when they share
  a name.** When a child project had its own epic with the same name and date
  as an epic above it, the tasks of the child's epic were counted toward the
  parent's epic, and could stop it from closing.
  - TCW now records which project an epic lives in when the epic's task sits
    in another project, for example `initiative: web/2026-01-01-redesign`.
  - `tcw work delegate --initiative` always records it, and so does
    `tcw work new --initiative` in a child project.
  - Existing links keep working as before.
