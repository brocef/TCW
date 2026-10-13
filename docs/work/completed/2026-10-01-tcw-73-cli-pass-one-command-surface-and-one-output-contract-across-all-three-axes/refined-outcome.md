# Refined outcome — TCW-73: one command surface and one output contract

**Accepted** on 2026-10-13 under the TCW 3.0 epic's rule: a child item is
approved at verify when it passes a bounded adversarial review (the owner,
2026-10-02: "You can also consider work approved if it passes adversarial
review, I will not review anything until we finish the epic"). The confirming
round ended `DONE`.

## What was accepted

Everything in `outcome.md`: the 3.0 command surface on all three axes, one
output contract (stdout carries only the product, stderr names every file
written or removed, one exit-code table), `tcw projects list`, `tcw validate`
over the current project and over one work item, taxonomy and capabilities
writing files only, `init` and `provision` on the contract, the `--help`
standard, the `projects` key in place of `connected-projects`, "project" in
place of "node" in the code, the shell scenarios that stay, and the 3.0 ledger
and taxonomy records. All 28 acceptance criteria are met; `outcome.md` gives
the evidence for each.

## Reviews

**Round 1** ran as three reviewers over separate parts of
`89ff245d..20f0b9f4`: the output contract and command surface; the stores and
git removal; the rename, the config key, the records and the scenarios. All
three ended `NOT DONE`. Their findings, with each fix's commit and test, are in
`outcome.md`'s "Review fixes" section (branch `e83c759f..bde41393`; spec notes
`debde570`). The ones that mattered most:

- `taxonomy rm` could delete a sub-folder a capability still named, leaving a
  dangling reference. **Narrowed:** the reviewer's fix (count every sub-folder
  as a nested term) would contradict Design 8.2's rule that a folder holding
  only a `.DS_Store` goes with its term. `rm` now refuses when anything refers
  to the term's folder or any folder inside it.
- A delete that failed partway removed files without naming them.
- The retired `connected-projects` key was refused only by some commands;
  `projects list` and `provision` exited 0 as if nothing were declared.
- A closed stdout printed "Exception ignored" and exited 120 for short output.
- `tags rm` of an unknown tag exited 0; `validate --remote` gave a false
  "backend is filesystem" error on a broken Jira config; a Jira create whose
  read-back failed lost the name of the ticket it made.
- The contract test passed with stray stdout added to several commands,
  including the real Jira edit and comment paths. It now runs an in-project
  case for every command and the real Jira backend against the fake.
- **Spec amended rather than code:** a rename prints `moved <old> to <new>`
  (Design 1.2); a present but unreadable connected project is a `warning` in
  `validate` (Design 6.2 note).

None rejected. Each code fix has a test that fails when the fix is undone.

**Confirming round** over the fixes: every finding resolved, no regression,
the S1 narrowing correct against the spec, `DONE`. Its one small fold-in — the
name a failed command prints on stdout was not flushed inside the handler, so a
closed pipe still exited 120 on that path — was fixed in `4cf97fd3`, with a
test that fails on the previous handler.

## Follow-ups

`docs/work/inbox/2026-10-13-tidy-what-tcw-73-s-reviews-left-for-the-cli.md`
(`11d76b60`, extended after the confirming round): `capabilities reset`
deleting nested local capabilities, unchecked `--slug`, gaps in the git-write
scan, git asking for a password during `provision`, stale names in
`docs/lifecycle/implementation.md`, a test that runs whatever `tcw` is on PATH,
`list` and `rm` disagreeing about a sub-folder with no `meta.yaml`, the
retired-key message's bare file name, and `work list` not noticing a child's
retired key. Already assigned: `tcw serve`'s output (TCW-77), the `review` and
`qa` prompts (TCW-74).

## Deferred, by the owner's instructions for this epic

- The full suite runs near the end of the epic. Here: targeted files only
  (listed in `outcome.md`); `pytest --collect-only -q` collects 3632 tests
  cleanly.
- README, guides and skills go to TCW-74 and TCW-75; the migration guide and
  removing `Planning doc`/`Tracker` from the records go to TCW-76.

## Capabilities

The records were written on the branch and pass the records gate there
(`outcome.md`, "Records gate"). They reach `main`'s ledger only when the epic
merges, so `tcw work complete` would refuse them on `main`. The item is
therefore completed by hand, as TCW-69, 70 and 71 were.

## Closeout route

The branch `work/2026-10-01-tcw-73-…` fast-forwards `epic/tcw-3.0`; its worktree
and branch are then removed. `main` receives 3.0 only when the epic ends. No
GitHub issue originated this item.
