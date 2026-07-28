# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Changelog entries no longer need to carry commit hashes

Until now, the documentation assistant asked you to wrap every developer
changelog entry in the range of git commits it came from, and to look those
commits up as part of writing the entry. That requirement is gone.

The hashes went stale as soon as anyone rebased, amended, or squashed — and the
release process carried a whole repair step for fixing ranges it had itself
invalidated. Both are removed. A changelog entry is now prose describing what
changed; searching your git history for it works the same as it always did.

Entries you have already written keep the hashes they have. Nothing is rewritten
and nothing you wrote under the old rule becomes invalid.

## The backlog audit now works in Codex, and it is faster

Asking the assistant to audit your backlog reviews every waiting item and reports
what has gone stale — work that already shipped, plans pointing at files that
moved, items too vague to pick up, duplicates, and blockers that were cleared long
ago. It reports and asks; it never changes anything on its own.

Two changes:

- **It works under Codex as well as Claude Code.** Previously the procedure was
  packaged in a way only Claude Code could see, so Codex users could not run it
  at all.
- **It reviews items side by side rather than one after another**, so a long
  backlog no longer takes proportionally longer to audit. Checks that only need
  one item are handled separately from checks that need to compare items — which
  also means it now catches a case it used to miss: an item that mentions
  depending on another one without that dependency ever being recorded, so both
  look ready to start.

## Three commands in the documentation did not exist

The README and the assistant-facing guides described `tcw work
audit-work-backlog`, `tcw work consolidate-plans`, and a `--pr` option on `tcw
work edit`. None of them were real — running the first two gave an error instead
of doing anything.

The first two are assistant-driven reviews rather than commands you type, and the
documentation now says so and explains how to reach them. The `--pr` option is
simply gone from the docs. A new check runs with the test suite and will fail the
build if any documentation ever again names a `tcw` command or option that does
not exist — including in the capability descriptions, which is where the last
surviving one was hiding.

Consolidating external plans is still Claude Code only; making it work in Codex
is tracked as separate work.
