# Refined outcome

**Accepted.** A mistyped subcommand now gets one extra line after argparse's
own error, naming the likely command:
- a word that exists one level down is named in full;
- a common synonym points at the real verb;
- a close spelling points at the closest verbs;
- removal words are never suggested.

`tcw work stage gate|prompt` given an artifact names the stage that writes it,
and given a transition names that transition's command.

## Evidence

- **`tcw:verifier`: all nine acceptance criteria met**, each with a named test.
  - Full suite, bare `pytest` at `f9e69d62`: 5071 passed, 3 skipped, 0 failed.
  - `--help` output for every parser is byte-identical to the merge base
    (1186 lines).
  - Under Python 3.12.13 the first error line is unchanged from the merge base.
  - `tcw validate` and `tcw capabilities check` pass.
- **Hands-on, in a scratch repository with the branch's code:**
  - `tcw tracker status` → `tcw work tracker show` or `list`;
  - `tcw work strat` → `start` or `stage`;
  - `tcw work status` → `show` or `list`;
  - `tcw work ls` → `list`;
  - `tcw work rm` gets no suggestion;
  - `stage gate refined-outcome` → the `verify` stage;
  - `stage gate start` → `tcw work start <slug>`.

## Found at verify

- **`status` suggests `list` wherever `list` exists**, not only at the `work`
  level as Goal 2 said. This was deliberate, since `tracker` and `inbox` have
  the same pair of verbs, and the capability text and changelog already
  describe it that way. Goal 2 was reworded to match.
- **The stage hints print `<slug>`, not the slug the user typed.** The hint is
  built while argparse rejects the stage word, before the slug is parsed.
  Left as it is: it is standard placeholder form.

## Deferred

- **Closing GitHub issue #69 waits for publication.** The order is: complete
  the batch → cut the version → push → answer and close, with the reply text
  approved first.
- **Adding Python 3.12 or 3.13 to CI** is filed in the inbox.
