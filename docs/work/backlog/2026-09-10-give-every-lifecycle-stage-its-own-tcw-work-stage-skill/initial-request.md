# Give every lifecycle stage its own `tcw-work-<stage>` skill

The `tcw-work-stage` skill takes two arguments: the stage id and the work item
reference. Both have to be typed in the right order for the skill to compose
anything, and the stage id is the one the invoker already knows for certain —
they came here *because* they are about to work the spec stage, or the plan
stage. Making them restate it is friction with no payoff.

Split the skill into one skill per lifecycle stage, named `tcw-work-<stage id>`.
Each of those knows its own stage, so the stage argument disappears. That leaves
the work item reference as the only argument, and it can be optional, because
`tcw work stage prompt` already accepts being called without one. The result is
a skill you invoke by naming the thing you are actually doing — `tcw-work-spec`
— rather than by parameterizing a generic one.

Keep `tcw-work-stage` as it is. It stays the general-purpose entry point for
anyone who wants to pass a stage id explicitly, and for any caller that has the
stage id as data rather than as knowledge.

## Constraints

- **Not all seven stages get a skill.** Only the stages a person actually
  drives: `request`, `spec`, `plan`, `implement`, `verify`. `inbox` is excluded
  because it runs before an item exists and takes no work item reference at all,
  so it would be a skill with no arguments wrapping a two-line command.
  `postmortem` is excluded because `tcw-post-mortem` already covers it, with a
  read-only agent behind it, and a second skill for the same stage would compete
  with it for the model's attention.
- **The new skill files are hand-written and guarded by a test**, not generated
  from a template at build time. The repository should not grow a code
  generation step for five small Markdown files. A test asserting that the
  expected set of stage skills exists, and that each still names its gate, is
  the guard.
- **Every session pays for a skill's name and description**, whether or not the
  skill is used. That is the cost being accepted here, and it is why the set is
  five and not seven.

## Notes

The requester was asked for reference material and answered that the repository
is enough — no external document, prior art, or related item to start from.

The existing skill's own warning has to survive the split. `tcw work stage
prompt` resolves instructions without running the legality check or the `pre`
bindings; `tcw work stage gate` is what refuses. Whatever each new skill says,
it has to keep saying that, and the parity tests that currently enforce it for
one file will have to enforce it for all of them.

Out of scope: any change to the `tcw` CLI, to the stage documents themselves, or
to what `tcw work stage prompt` emits. This is a change to how the skills are
packaged and invoked, nothing more.

## References

- `skills/tcw-work-stage/SKILL.md` — the skill being split; its two-argument
  frontmatter and its gate warning are what the new skills inherit.
- `tests/test_skill_lifecycle_parity.py` — already guards the composing skill's
  path template, its gate warning, and its `|| true` guards. The tests that keep
  the split honest belong next to these.
- `tcw/store/base.py` — `STAGE_IDS` is the public list of stages, and the
  authority on what a valid `<stage id>` is.
- `docs/capabilities/work/run-a-lifecycle-stage/description.md` — the standing
  capability this change alters the shape of.
