# Post-mortem — Audit the work backlog with subagents, and make the workflow reachable from Codex

Requested by the user after closeout. Out-of-band: this changes nothing about the
item's `completed` status.

The item shipped successfully, so this is not an incident review. It is worth
running because a defect **passed verification** and was caught only by an
unplanned empirical trial — and because the same mistake recurred three times
inside one item, which is the signature of a cause rather than an accident.

## What went wrong

### Finding 1 — the sweep for sibling defects was scoped to where the first one was found

Three manifestations, one cause.

**(a) The one that shipped past verification.** The spec's AC4 read: *"**No file
in the repo** documents `tcw work audit-work-backlog`, `tcw work
consolidate-plans` … or `tcw work edit --pr`."* Universally quantified, over the
repo. But every check of it enumerated four directories — `README.md`, `skills/`,
`commands/`, `agents/`:

- **spec** (`5a73482`) swept `commands.md` and `README.md`, found two extra
  phantoms, and recorded them in D6;
- **implement** (`6e63405`) wrote the guard test with those same four roots;
- **verify** grepped those same four roots and reported AC4 met.

`docs/capabilities/work/consolidate-plans/description.md:1` was outside all
three, and kept claiming a CLI verb that never existed. The trial agent found it
because it scanned differently.

**(b)** The spec predicted the stale "Codex has no subagents" claim in two places.
It was in three — `delegation.md` asserted it twice, and that was found only by
opening the file during implementation for an unrelated reason.

**(c)** The D6 decision to defer the `consolidate-plans` migration was made
without opening `commands/tcw-consolidate-plans.md`. That file carries
`disable-model-invocation: true` because the workflow deletes files — a safety
constraint that materially changes the deferred item. The trial agent found it.

**Nobody could have known, or nobody checked?** Nobody checked, in all three. The
capability file was on disk and readable throughout; `grep -rn "tcw work
consolidate-plans" .` would have returned it at spec time, in one command. The
`delegation.md` duplicates would have fallen out of `grep -rn "Codex has no" .`.
The `disable-model-invocation` flag was the third line of a file the spec named
but did not open. Every one was available at the spec stage.

### Finding 2 — a false claim was inherited from cited precedent

The spec justified `agents/tcw-backlog-auditor.md` by mirroring
`agents/tcw-verifier.md`, and copied its hard limit verbatim: *"You have no write
tools."* Both hold `Read, Glob, Grep, Bash`, and `Bash` writes. The precedent's
**shape** was verified (read-only agent, same tool profile, passes
`delegation.md`'s custom-agent test); the precedent's **claim** was not.

The spec then escalated it, asserting the tool set "enforces this rather than
requesting it" — a guarantee neither agent provides. Caught at verify, before
shipping, but it had already been written into four files.

Nobody could have known, or nobody checked? Nobody checked. The tool list and the
claim contradicting it were four lines apart in a file read in full during spec.

## Which stage could first have caught it

**The `spec` stage, for every finding above.** Not `implement`, not `verify`.

The information was on disk and readable at spec time in all four cases. What
`implement` and `verify` contributed was worse: **they reused the spec's scope
instead of re-deriving it from the criterion.** AC4 said "no file in the repo";
the test enumerated four roots because the spec's sweep had; verification grepped
four roots because the test did. Three stages, one blind spot, inherited
downstream — which is precisely the failure mode independent verification exists
to prevent, and it did not prevent it because the verification was not
independent.

Cost of catching it at spec: **one `grep -rn` per defect instance.** Cost of
catching it where it was actually caught: a full implement–verify cycle, a
completed-and-reported-met acceptance criterion that was false, and an unplanned
12-subagent trial run that only happened because the user asked for one.

## What would have had to be different

**For finding 1, a mechanism rather than a rule.** The guard test enumerates the
directories it scans. Flip it to enumerate by *exclusion* — every `*.md` in the
repo except the archival trees — and the class of defect becomes uncatchable by
scope error, because there is no scope to get wrong.

I verified this is viable rather than assuming it: scanning every `*.md` outside
`docs/work/`, `docs/changelogs/`, `docs/release-notes/`, `docs/plan/`, and
`docs/superpowers/` produces exactly **three** failures, all in archives —
`docs/plan/phase-5-work.md` (`tcw work rename`) and two `docs/superpowers/`
documents (`tcw work block`, `unblock`, `check`). Those trees are records of what
was decided at a point in time, the same class as `docs/work/`; excluding them is
principled, not an ad-hoc allowlist to make a test pass.

This is the better fix because it replaces judgment with a mechanism, matching
the repo's own directive that anything which must be guaranteed belongs in the
tooling rather than in an instruction someone has to remember.

**For the residue the guard cannot see** — a false factual claim in prose
(`delegation.md`), a safety flag in a file the spec named but did not open — no
mechanism applies, so a narrow rule at the spec stage does: *when a spec records
a defect instance, the sweep for siblings is repo-wide by default; if narrowed,
the spec states the scope and why.* That is checkable by reading a spec, not a
disposition. It fired three times in this one item.

**For finding 2**, the candidate rule is *"citing precedent requires verifying the
precedent's claim, not just its shape."* **I do not recommend adopting it.** It
fired once, the existing verify stage caught it before it shipped, and as written
it generalizes into "check everything you cite" — which is a wish, not a change.
The concrete residue was worth fixing and has been fixed (four files corrected,
including the pre-existing false claim in `tcw-verifier`). Adding process for it
would cost more than the failure it would prevent.

## Worth making?

| Change | Verdict |
|---|---|
| Guard test: inclusion-list → exclusion-list | **Yes.** ~5 lines, verified viable, closes the defect class that shipped |
| Spec-stage rule: state the sweep's scope | **Yes.** One line; the miss it addresses fired three times in this item |
| Rule about verifying cited precedent | **No.** Fired once, was caught, and generalizes into "be more careful" |

## Notes

Two honest limits on this analysis.

**The trial run was not part of the process.** It happened because the user asked
for one, and it is what caught the finding-1 defect. Nothing in the lifecycle
schedules an empirical trial of a shipped judgment-layer change, and I am not
proposing one — for most items it would be pure cost. But this item's central
deliverable was a *procedure for agents*, and the only way to know whether a
procedure works is to run it. That the check was ad-hoc is worth noticing, even
though the general fix is not obviously worth building.

**The strongest evidence here came from an agent whose two headline claims were
wrong** (it misdiagnosed a stale plugin cache as document drift, and misread `tcw
work new`'s file hint as the folder location). Both were caught by re-checking
before relaying. Its own process appendix named the reason: it never re-verified
its subagents' citations. The lesson generalizes past this item — a delegated
finding is a lead, and the coordinating session owes it a spot-check before
acting.
