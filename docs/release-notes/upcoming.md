# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is the release v2.5.0 was meant to be.** v2.5.0 was tagged but never
reached PyPI, because a test that only failed on the build server stopped the
upload. Everything described in the
[v2.5.0 notes](v2.5.0.md) (making Jira tickets with `tcw work tracker create`,
and moving `extends` into `tcw-config.yaml`) arrives with this version.
**Read those notes before upgrading if you use inheritance**, because that part
needs a migration step.

### An old inheritance file is now pointed out

Before 2.5.0, a project that inherited another project's taxonomy or
capabilities listed it in a file inside the tree:
`docs/taxonomy/config.yaml` or `docs/capabilities/.config.yaml` (or the same
file wherever you keep that tree). 2.5.0 stopped reading those files, and a
project that did not move the list lost every inherited entry without a word.

Now `tcw taxonomy check`, `tcw capabilities check` and `tcw validate` report
such a file, and tell you what to do: copy any `extends` you still need into
`tcw-config.yaml` (under `taxonomy:` or `capabilities:`), then delete the file.
If you already copied it, just delete the file.

**This can make a previously passing project fail.** A file you migrated but
kept now fails `check` and `validate` until it is deleted — and so it can stop
`tcw work complete` in any project that runs `tcw validate` before completing.
TCW never edits or deletes the file for you.

Two smaller changes come with it:

- `tcw validate` now also reports a taxonomy or capabilities tree that is kept
  in another repository and has not been downloaded to this machine yet, and
  tells you to run `tcw provision`. It already did this for the work board. If
  such a project runs `tcw validate` before completing work, completing can be
  refused until `tcw provision` has run.
- When a capability overrides one from a project you do not inherit from, the
  "unknown alias" problem now says the project is missing from
  `capabilities.extends` in `tcw-config.yaml`.
