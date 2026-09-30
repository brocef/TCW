# Run CI on Python 3.12 or 3.13 as well

From the adversarial review of #69
(`2026-09-29-suggest-what-was-meant-when-a-subcommand-or-stage-name-is-wrong`).

`requires-python` is `>=3.11`, but `.github/workflows/test.yml` runs only 3.11
and 3.14. argparse's "invalid choice" wording differs on 3.12 and 3.13 (the
choices are unquoted), and a change that rebuilt that message looked correct on
both CI versions while changing the text on the two in between. Add one of them
to the matrix.
