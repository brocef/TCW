# Refined outcome

**Decision: accept (made autonomously, per the run's rules).**

- Final full suite at `0ff05c56`: 4836 passed, 3 skipped. The commits after
  it change only docs and state files.
- `tcw:verifier`: all 5 criteria met, no defects found.
  - All 5 new tests fail on the merge-base code, each for its intended
    reason.
  - All 4 reproductions were rebuilt by hand. The old code fails each one;
    the new code passes each one.
  - Extra layouts also checked: a submodule inside a linked worktree of the
    outer repository, a primary-checkout submodule, and a bare repository's
    worktree.
- My own check, driving the real `tcw validate` on layouts I built by hand:
  - **Letter-case locator:** the installed old `tcw` reports a duplicate
    `root` and a parent locator that does not point back. The worktree's
    code reports "validate OK".
  - **Symlinked config:** the old `tcw` warns that `kid` is not reachable.
    The new code reports "validate OK" with no warning.
- One behavior change beyond the fix: two folders sharing one config
  through a symlink now report a duplicate id instead of a mismatched key.
  That layout was invalid before and is invalid now, so only the message
  differs.
- A decision to review: question 3 (overrides keep the checkout they name)
  split the advisors. It is recorded in `outcome.md` and tracked by
  `2026-09-29-warn-when-a-project-override-names-the-primary-checkout-s-copy-from-a-linked-worktree`.
