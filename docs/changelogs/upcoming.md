# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Changed

- `tcw/work/prompts/implement.md` step 3 now says what to do when a new test
  passes on its **first** run: break the behaviour it names and confirm it goes
  red. The rule was rewritten into step 3 rather than appended as a tenth step —
  steps 4-9 keep their numbers, and a list whose third entry went unfollowed is
  not repaired by gaining a tenth entry.

  Earned rather than invented. Across the three children of the
  store-provisioning epic, five defects reached `verify` or an external review
  from behind green tests, and three times an author met a green new test and
  explained it instead of distrusting it — each explanation locally true. The
  sharpest case asserted `"diverged" in err`, matched *git's* push-rejection
  hint, and stayed green while TCW's own message was still wrong. Breaking the
  behaviour surfaces that in seconds; no amount of care about coverage does.

### Internal

- `docs/lifecycle/implementation.md` gains the narrower sibling rule, bound to
  this project only: when asserting a user-facing message, assert that the
  message it replaces is absent. An assertion aimed at a string another program
  owns is not a test of this one.
