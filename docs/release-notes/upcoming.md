# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixed

- **Codex users: the work skill loads again.** Codex was skipping the `tcw-work`
  skill entirely and reporting an invalid skill file, because the file was
  missing the header block Codex requires. That header is back, so Codex now
  loads every skill in the plugin. Claude users were unaffected. A test now
  checks the header on every skill so it cannot go missing again.
