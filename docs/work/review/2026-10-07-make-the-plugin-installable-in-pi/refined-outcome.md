# Refined outcome — Make the plugin installable in Pi

**Accepted, 2026-10-15**, by the owner's decision to publish 2.8.2 with this
work before the TCW 3.0 code freeze ("Publish 2.8.2 first": merge the Pi
branch into main, push the tag, complete the Pi item).

## Released

- Published as **tcw-cli 2.8.2** (tag `v2.8.2` at `74630308` on main; release
  workflow run 38799722986 succeeded). `pip install tcw-cli==2.8.2` into a
  fresh environment installs it and `tcw --version` prints `tcw 2.8.2`.
- The tag's `package.json` carries the `pi` block
  (`skills: ["./skills/*/SKILL.md"]`, no extensions, prompts or themes).

## Fixed at release

CI on `879ceeef` failed one test: the Pi rewrite of
`docs/lifecycle/harness.md` dropped the "Agentskills specification" link that
`tests/test_repo_lifecycle.py::test_the_moved_rules_are_reachable` requires.
Restored as a fact about Codex (`74630308`). The full suite then passed on the
release commit (5231 passed, 3 skipped) before the tag was pushed. The tag
`v2.8.2`, never pushed before, was moved from `5d672a6b` to that commit.

## Not verified

A remote install through Pi from the published repository, and an agent
running a lifecycle stage under Pi, as `outcome.md` already says.

## For TCW 3.0

The epic's rewritten README and `harness.md` do not carry this item's Pi text;
TCW-76 resolves that when it merges `main` into the epic.
