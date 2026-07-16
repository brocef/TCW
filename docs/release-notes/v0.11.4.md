# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

- You can now change the status of a capability your project inherits from
  another project, using the same command you already use for your own
  capabilities: `tcw capabilities set <path> --status Supported`. It previously
  failed with "no such capability" for anything inherited, even though the same
  path worked with `show` and appeared in `list` — so the only way through was
  hand-writing the file, which the guidance tells you not to do. The local
  override file is now written for you. Editing an inherited capability in the
  web app works for the same reason.
- When a capability name matches more than one project you inherit from, the
  error now says so and tells you to add the alias prefix, instead of printing
  the name back at you with no explanation.
