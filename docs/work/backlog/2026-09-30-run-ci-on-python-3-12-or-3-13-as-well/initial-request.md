# Run CI on Python 3.12 as well

## What is wanted

CI should test a Python version between the two it runs today.
`requires-python` is `>=3.11`, but `.github/workflows/test.yml` runs only 3.11
and 3.14. argparse's "invalid choice" wording differs on 3.12 and 3.13 (the
choices are not quoted there), and a change that rebuilt that message looked
correct on both CI versions while changing the text on the two in between.

**Decided with the maintainer at triage:** add **3.12** to the test matrix. Not
3.13, and not both.

## Constraints

- The suite is already slow (see
  `2026-09-24-make-the-test-suite-run-in-minutes-not-half-an-hour`); one extra
  leg is the accepted cost.

## Notes

- From the adversarial review of #69
  (`2026-09-29-suggest-what-was-meant-when-a-subcommand-or-stage-name-is-wrong`).
- The title still says "3.12 or 3.13" from the entry; the decision is 3.12.
- Reference material: asked; none provided beyond the entry.
