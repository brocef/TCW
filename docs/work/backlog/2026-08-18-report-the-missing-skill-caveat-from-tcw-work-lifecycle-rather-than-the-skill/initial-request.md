# Report the missing-skill caveat from tcw work lifecycle rather than the skill

Filed by the C8 audit of
`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`. Identified in
C7's spec §7 as a candidate to move into the CLI, and deliberately deferred
there because C7 was not touching `tcw/` outside the prompts.

## Product changes

`skills/tcw-work/references/hooks.md:83` carries this caveat:

> **A configured-but-missing skill cannot fail closed everywhere.**

It is **harness-neutral operating advice about a real hazard** — a node
configures a `skill:` binding, the skill is not installed, and nothing stops the
work proceeding as though it had run. And it lives in the one place a user
without the plugin never looks.

That is the same defect this epic spent seven children fixing everywhere else:
judgment that only a Claude user with the plugin installed ever receives. The
epic's own rule, from `CLAUDE.md`: *anything that must be guaranteed belongs in
the `tcw` CLI, which behaves identically under both harnesses.*

The natural home is `tcw work lifecycle`'s output, beside a reported `skill:`
binding — the moment a user is looking directly at the binding the caveat is
about.

## Technical changes

**This is a CLI behaviour change, not a docs move**, which is why it is its own
item rather than part of C7:

- `tcw work lifecycle` gains output it did not have. That is user-visible, so it
  carries a capability delta — most likely a revision of
  `work/inspect-the-lifecycle-contract` (`cap-95e225`).
- The epic's acceptance criterion 12 pins that `tcw work lifecycle` **executes
  nothing**. Adding a line of output must not weaken that; re-verify it.
- Decide whether the caveat prints always, only when a `skill:` binding is
  present, or only when one is present *and* unresolvable — the last is the most
  useful and the only one that needs to know anything about the environment.
- Decide whether `hooks.md` keeps its copy. C7's rule was that the CLI states the
  obligation and the skill names what discharges it; the same split may apply.

## Meta changes

If the caveat moves rather than duplicates, `skills/tcw-work/references/hooks.md`
loses a line — but note C7 just consolidated that file from 159 to 92 lines, so
check its current shape rather than an older one.

## References

- `docs/work/completed/2026-08-12-repoint-the-work-skill-and-docs-at-the-cli/spec.md`
  §7 — where this was analysed and deferred, including the reasoning for
  "recommend, do not do".
- `CLAUDE.md` §"Harness compatibility (Claude and Codex)" — the rule that decides
  this.

## Notes

- The smallest of the three C8 filings in diff size and the largest in blast
  radius: it is the only one that changes what the CLI prints.
