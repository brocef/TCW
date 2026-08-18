# Migrate TCW itself to the 1.0.0 lifecycle and write the consumer migration guide

v1.0.0 is cut and tagged but not yet pushed. Before it goes out, two things are
wanted, in this order:

**1. A migration guide for TCW consumers, 0.21.x → 1.0.0.** The repo already has
four of these (`docs/migration-guide-*.md`) and 1.0.0 carries a real back-compat
break, so it earns one. It should tell a consumer what they actually have to
change — which, on inspection, is very little — without burying that under the
much longer list of things 1.0.0 newly makes possible. The release notes already
sell the features; the migration guide's job is to answer "what breaks, and what
do I do about it", quickly.

**2. Migrate this repo onto the new lifecycle configuration.** TCW's own
`tcw-config.yaml` declares only an `id` and a tag list. It configures no
lifecycle at all, which means the headline feature of 1.0.0 — a project binding
its own instructions, checks, and templates to lifecycle stages — has never been
exercised by the project that ships it, on the project that ships it.

The migration is to exercise the full 1.0.0 configuration surface against this
repo's real rules: stage `prompt:` bindings composed with `builtin: true`, at
least one `pre:` check, and `artifacts:` templates. Not a demo — the bindings
should carry rules this repo genuinely has, so that if the configuration surface
cannot express them, that is a finding worth having before 1.0.0 ships.

The rules in question are the ones currently written in `CLAUDE.md`: the
abstraction litmus test, the requirement that spec and plan documents live in
the work item folder, the documentation-sync gate, and the Claude/Codex harness
parity rule.

**Once a rule is bound to a stage, remove it from `CLAUDE.md`.** Two copies will
drift, and a project that keeps the prose in `CLAUDE.md` has not really migrated —
it has just added a second place to read the same thing. This is the part of the
work most likely to be wrong, and it is deliberately the point: it tests whether
the new configuration surface is trustworthy enough to be the only carrier of a
rule.

## Constraints

- **Nothing is pushed.** v1.0.0 is tagged locally on
  `epic/polymorphic-work-lifecycle`, which is unmerged. This work happens on top
  of that state; publishing stays a separate human decision.
- **Codex parity applies to the outcome.** If the repo's rules end up reachable
  only by an agent that runs `tcw work stage`, that has to be true for a Codex
  agent as well as a Claude one — which is the design's own claim, so this is a
  direct test of it.
- The guide follows the house style of the existing four: prose, plain language,
  organized around what the reader must do rather than around the diff.

## Out of scope

- Pushing, merging `epic/polymorphic-work-lifecycle`, or publishing to PyPI.
- Any change to the 1.0.0 CLI itself. If dogfooding surfaces a CLI defect, it
  gets filed as its own work item, not fixed here — unless it makes this item
  impossible to finish, in which case say so rather than working around it.
- Retro-fitting the earlier migration guides to a common template.

## Notes

- Asked for additional reference material; none provided beyond what is already
  in the repo.
- Checked before writing this: this repo **breaks nothing** on upgrade. There is
  no `prompt: []` anywhere, `tcw-config.yaml` has no `lifecycle:` block, and the
  one epic's rollup already lives in `rollup.md` rather than inside its request.
  So "migrating this repo" is entirely adoption, not repair — which is worth
  knowing, because it means the repo cannot serve as a test of the repair path.
- Whether a bare one-line pointer to `tcw work stage` survives in `CLAUDE.md`
  after the prose is removed is a spec-stage detail, not a decision made here.
- The `tcw-work` skill loaded from the plugin cache during this session was
  version 0.21.1 and predates the 1.0.0 CLI it was driving — it still directs
  readers to `tcw work lifecycle --stage <id>` rather than `tcw work stage`. The
  repo's own `skills/tcw-work/SKILL.md` is current. This is a consumer-facing
  upgrade-ordering problem and belongs in the migration guide.

## References

- `docs/release-notes/v1.0.0.md` — the user-facing account of everything 1.0.0
  changed; the migration guide is written against it and must not merely repeat
  it.
- `docs/changelogs/v1.0.0.md` — the precise, technical statement of the break
  (`## Removed`, `prompt: []`) and of the behavior changes a consumer's scripts
  could be resting on.
- `docs/migration-guide-0.15.X-to-0.16.0.md` — the closest prior art in tone and
  shape: a release with almost nothing to do, which says so up front and then
  explains the optional cleanup.
- `docs/migration-guide-0.10.X-to-0.11.0.md` — the longest of the four; the
  reference for how this repo handles a migration that does demand real work.
- `docs/work/completed/2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven/` —
  the epic that produced 1.0.0, including its `rollup.md`; the authority on what
  the lifecycle configuration was designed to support.
- `CLAUDE.md` — the source of the rules being migrated into stage bindings, and
  the file the second half of this work edits.
- `README.md` lifecycle-binding section — the documented contract for `prompt:`,
  `pre:`, `artifacts:`, `when:`, and `generate:` that the new config must obey.
