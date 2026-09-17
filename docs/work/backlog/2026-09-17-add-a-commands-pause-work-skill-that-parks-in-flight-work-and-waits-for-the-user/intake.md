# Add a commands-pause-work skill that parks in-flight work and waits for the user

TCW's plugin ships command skills for starting and finishing work — `commands-plan-work`,
`commands-drive-work-to-completion`, `commands-verify-work`, `commands-process-inbox` — but
nothing for stopping mid-flight. A user who needs an agent to stand down right now has no
instruction to invoke, so the agent either stops wherever it happens to be (leaving the
working tree, the item's artifacts, and the claim in whatever half-state the interruption
found) or keeps going.

Add a `commands-pause-work` command skill that:

- stops the work in progress **gracefully** rather than abruptly — finishing or backing out
  of whatever is mid-edit so the checkout and the item are left in a coherent state;
- writes whatever notes resuming needs into the relevant `tcw work` item(s), so the next
  session (or the same one after a gap) can pick the work up from the board rather than
  from chat scrollback;
- then **waits** — it does not complete, discard, or hand the item on; it holds until the
  user says to continue.

Open questions for the spec stage: what exactly counts as "gracefully" when an edit is
half-applied; where the resume notes belong (an artifact, an append to an existing one, or
item state); whether pausing releases the item's claim or keeps it; whether the item stays
`active` or moves; and whether the skill commits the work in progress or leaves it
uncommitted.

## Origin

Asked for directly in chat on 2026-09-17: "Create a new command skill in the TCW repository
called commands-pause-work. The purpose of this skill is to have an agent stop the work it's
doing (gracefully), make any notes it needs to resume in the relevant TCW work items, and
wait for the user to tell it to continue."

## References

- `skills/commands-drive-work-to-completion/SKILL.md`, `skills/commands-plan-work/SKILL.md`,
  `skills/commands-verify-work/SKILL.md`, `skills/commands-process-inbox/SKILL.md` — the
  four existing command skills; the new one has to match their shape, frontmatter, and the
  way they route through the `work` and `work-stage` skills rather than restating stages.
- `skills/README.md` — the rules a skill in this plugin follows, including `dynamic_skill`
  and which skills a project may override.
- `docs/work/backlog/2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability/` —
  related: it holds that every skill gets one capability and that skills must work under
  Codex as well as Claude, both of which this new skill has to satisfy on arrival.
- `docs/work/backlog/2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app/` —
  related, not blocking: it covers recovering a claim left behind by a process that *died*.
  A graceful pause is the case where nothing died, so it should not need take-over — but
  whether pausing keeps or releases the claim decides whether the two ever meet.
- `docs/work/backlog/2026-09-16-point-open-work-items-at-the-renamed-skills/` — related: any
  new command skill name lands in the same set of references that item is reconciling.

No blockers: the board search turned up no item this one has to wait on (searched
`tcw work list`, `tcw work inbox list` — empty — and `tcw work list --all`).
