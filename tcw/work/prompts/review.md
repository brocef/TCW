# Stage: review

**Purpose.** Check the code against the spec and the plan, including that the
taxonomy and capability records changed with it and say what the code does.
A move past implement already checked that the declared records exist; this
stage checks that they are right.

**Inputs.** The spec and plan (`tcw work path <slug> spec` and `plan`), the
newest round in `tcw work path <slug> implement`, `capabilities.yaml` in the
folder `tcw work path <slug>` prints, and the code itself. Read the change
through what the implement round says changed; how the project shows a change
to its reviewers is its own choice. Repository discovery is unrestricted.

**Resuming.** Read the newest `handoff-*.md` in `tcw work path <slug> review`,
as a description of the work when it was written, and check for anything newer
before trusting it. To leave one, write it to
`tcw work path <slug> review --handoff`.

**Produce** one round at `tcw work path <slug> review --next`, starting with
this front matter:

```yaml
---
verdict: accepted        # or rejected
judges: 3                # the newest implement round
---
```

`judges` is the highest `N` among the `round-N.md` files in
`tcw work path <slug> implement`, or 0 when there are none. A wrong number
makes the verdict stale, and a stale verdict lets nothing through. Under the
front matter, list each acceptance criterion as met, not met, or not
checkable, with the evidence for each.

## Steps

1. Run the project's checks. **No claim without output from a command you ran
   just now.**
2. Go through the acceptance criteria one at a time, against the code, not
   against the implement round's account of it.
3. Check every path in `capabilities.yaml` against its record: present, and
   describing what the code now does. A record that names behavior the code
   does not have is a rejection.
4. Decide. `accepted` only when every criterion is met or the round says why
   one that is not checkable does not matter. Otherwise `rejected`, saying
   what implement must do.
5. Write the round. You may record the verdict yourself.

## Exit badly

- _A criterion cannot be checked as written._ Say so in the round; it is a spec
  defect worth recording, not something to wave through.
- _The spec solved the wrong problem._ A rejection will not fix that. Say so,
  and return the item to spec with `tcw work advance <slug> --to spec`.
