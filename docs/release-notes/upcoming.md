# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Improved

- `tcw validate` now checks the active project and all registered descendant
  projects by default, so one command catches problems throughout a project
  tree. Use `--no-recurse` when you only want to check the active project;
  passing a path also remains limited to the active project.
- Taxonomy inheritance now follows multiple levels of registered projects. If
  your project inherits a project that inherits another, terms from both are
  available under the project ID that owns them.
