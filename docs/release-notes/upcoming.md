# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is the release v2.5.0 was meant to be.** v2.5.0 was tagged but never
reached PyPI, because a test that only failed on the build server stopped the
upload. Nothing else changed: everything described in the
[v2.5.0 notes](v2.5.0.md) (making Jira tickets with `tcw work tracker create`,
and moving `extends` into `tcw-config.yaml`) arrives with this version.
**Read those notes before upgrading if you use inheritance**, because that part
needs a migration step.

### Also in this release

- **Your agent now tells you when the `tcw` command and the plugin's skills
  come from different releases.** It names both versions and the one command
  that brings them into line — updating the plugin, or upgrading the `tcw`
  command. It is only a warning and never stops your work. Claude shows it when
  a session starts; in Codex, the skills ask the agent to run the check.
