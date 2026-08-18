# Serve documentation-sync entries from tcw-config.yaml instead of scraping the agent guide

Documentation-sync is the last thing in TCW that gets its instructions by
name-matching a Markdown section in `CLAUDE.md`. Everything else moved to
configuration TCW itself serves when v1.0.0 landed the polymorphic lifecycle;
this did not, and it should be handled the same way. **Use the same prompt
generation for documentation sync as for the lifecycle stages.**

This surfaced at the verification of
`2026-08-18-migrate-tcw-itself-to-the-1-0-0-lifecycle-and-write-the-consumer-migration-guide`,
where it was written down as a limitation to work around. That was the wrong
call. It is a defect in the layering, and it is TCW's own prompts that carry it:

- `tcw/work/prompts/plan.md:20-21` — "Evaluate every Documentation Sync entry in
  the project's agent guide (`AGENTS.md` or `CLAUDE.md`)…"
- `tcw/work/prompts/implement.md:27-28` — the same instruction at the gate.

In the release whose stated point is that TCW tells you what to do at each stage,
TCW tells you to go and read a Markdown section out of a file it does not own,
in a format nothing validates.

## What is wanted

The entries — a file path, a trigger, and a description of what to write — are
**project configuration**, no different from `work.tags` or `work.lifecycle`, and
they belong in `tcw-config.yaml`. The instructions that consume them are generic
and belong in TCW's built-in prompts. Getting that split right means:

- `tcw work stage plan` and `tcw work stage implement` print the project's actual
  documentation entries, rather than telling the agent where to go looking.
- A project can extend or override that text through the bindings it already
  has — `builtin:`, `blob:`, `file:`, `generate:`, `when:` — exactly as it can
  for any other stage instruction.
- `tcw validate` catches a malformed entry or an unknown trigger, which nothing
  does today.
- The gate becomes reachable identically under Claude and Codex, because it is
  the CLI rather than a convention about reading agent guides.

## Constraints

- **Nothing that exists today may break.** A project with a
  `## Documentation Sync` section in its agent guide and no new configuration
  must keep working exactly as it does now. Configuration wins where present;
  the agent-guide fallback stays for everyone else. Adoption is opt-in.
- **This folds into v1.0.0**, which is tagged locally and unpushed. It is not a
  follow-up release. The point is that 1.0.0 should not ship with its own
  prompts pointing at a scraping convention, and folding keeps the migration
  guide written for 1.0.0 from being made half-wrong a week later.
- The `documentation-sync` skill has three invocation points, not one — `plan`,
  the end of `implement`, and the version offer after `complete`. The third is
  not a stage, so whatever is built has to serve it too.
- Whatever ships must let this repository finally move its own
  `## Documentation Sync` section out of `AGENTS.md`. If it cannot, it has not
  solved the problem that prompted it.

## Out of scope

- Changing the trigger vocabulary itself (`Public-API`, `Public-{Name}-API`,
  `Any-Code-Change`, `Only-Breaking`, plus project-defined ones). It is being
  moved and validated, not redesigned.
- The `## Versioning` section, which the skill also reads out of `CLAUDE.md` by
  name. Same class of problem, but a separate decision — flag it if the work
  makes the fix obvious, do not fold it in silently.
- Rewriting the four earlier migration guides.

## Notes

- Decisions taken with the user before this was written: fold into the unpushed
  v1.0.0 rather than ship a v1.1.0; configuration wins with the agent guide as
  fallback rather than a second breaking change; and the migration item that
  surfaced this was completed rather than reworked, so the two diffs stay
  separately reviewable.
- Consequence for already-shipped work: the migration guide
  `docs/migration-guide-0.21.X-to-1.0.0.md` currently advises readers to check
  what reads their agent guide before emptying it, and gives
  `documentation-sync` as the case that cannot move. Once this lands, that advice
  describes a fixed bug and has to be rewritten rather than merely amended.
- TCW's `Builtins` are static text loaded from `tcw/work/prompts/*.md` by
  `load_builtins()` (`tcw/work/resolve.py:47`). Rendering per-project entries
  into a built-in prompt is the part of this with no existing precedent, and is
  where the design attention should go.

## References

- `tcw/work/prompts/plan.md` and `tcw/work/prompts/implement.md` — the two
  built-in prompts carrying the defect; the change is visible here first.
- `skills/documentation-sync/SKILL.md` — the skill to be repointed; line 8 is the
  CLAUDE.md name-match, line 117 is the Versioning one that stays out of scope.
- `tcw/work/resolve.py` — `load_builtins`, `resolve_prompts`, `resolve_artifact`;
  the machinery the entries have to flow through for this to be "the same prompt
  generation".
- `tcw/store/base.py` — `parse_lifecycle_policy` and the binding parser, the
  precedent for how a new `work.*` config block is parsed and validated.
- `tests/test_documentation_sync_wiring.py` — what currently pins the skill to
  the lifecycle; `test_lifecycle_invokes_documentation_sync` is the test most
  likely to need rewriting.
- `tests/fixtures/lifecycle_baseline/` — the back-compat corpus. A change to the
  built-in prompts moves `self.json` and possibly other rows; the corpus is the
  evidence that the fallback path still renders as it did.
- `docs/work/completed/2026-08-18-migrate-tcw-itself-to-the-1-0-0-lifecycle-and-write-the-consumer-migration-guide/`
  — the item that surfaced this, including the guide that will need rewriting.
