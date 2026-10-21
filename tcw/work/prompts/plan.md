# Stage: plan

**Purpose.** Decide _how_, in ordered steps someone else could follow, so that
sequencing problems are found here and not halfway through implementing.

**Inputs.** The spec, at `tcw work path <slug> spec`, and the request:

{{tcw:request}}`tcw work show <slug>` prints it.{{/tcw:request}}

Repository discovery is unrestricted.

**Resuming.** Read the newest `handoff-*.md` beside the file
`tcw work path <slug> plan` names, as a description of the work when it was
written, and check for anything newer before trusting it. To leave one, write
it to `tcw work path <slug> plan --handoff`.

**Produce** the plan, at `tcw work path <slug> plan`: ordered steps, each naming
the **exact files it creates or changes** and what proves it is done; a
**Documentation Sync** block; and a **Verification** section for anything the
tests cannot check.

## Steps

1. Order the steps so the tests pass after each one. A step that leaves things
   broken for the next is two steps.
2. Put the riskiest change where it is _isolated_: after what it depends on
   exists and its tests are written.
3. {{tcw:documentation}}Evaluate every Documentation Sync entry in the project's agent guide
   (`AGENTS.md` or `CLAUDE.md`) and name a step for each trigger that will
   fire.{{/tcw:documentation}} Where the TCW plugin is installed, invoke the `documentation-sync` skill
   to do this. Schedule those steps as one block at the end.
4. If `capabilities.yaml` is missing from the folder `tcw work path <slug>`
   prints and the request names product changes, write it now, as spec would.
   If the item has no `QA plan` comment in `tcw work show <slug>`, post one
   with `tcw work comment <slug>`, as spec would.
5. Record dependencies between items as blockers, not prose:
   `tcw work edit <slug> --blocked-by <ref>`.
6. **Too large for one item?** Split it here: `tcw work new "<title>" --parent
   <slug>` for each part, the part's request on stdin, and plan this item as
   the parent that ties them together. A part that belongs to another project
   is filed with `tcw work new "<title>" --project <id>`, which takes no
   `--parent`. TCW leaves what it wrote there as uncommitted changes, so next
   record them in that project's version control, the way that project does,
   and set `--parent` and any `--blocked-by` with `tcw work edit` run from
   inside that project. File the next part there only once they are recorded:
   until then a filing is refused, or, where that project keeps its work in
   Jira, its ticket stays in the Jira inbox.
7. **No placeholders.** "TBD", "add error handling", "as in step 3": a step
   nobody can carry out without asking you a question is not a step.
8. **Self-review.** Re-read the plan against the spec: every acceptance
   criterion is covered by a step and every step traces back to one; names
   are consistent; no step appears twice.

## Exit badly

- _Planning shows the spec is wrong._ Return to spec and fix it:
  `tcw work advance <slug> --to spec`. Do not plan around a spec you have
  stopped believing.
- _A step cannot be verified._ Say so in the step rather than inventing a test
  that would pass either way.
