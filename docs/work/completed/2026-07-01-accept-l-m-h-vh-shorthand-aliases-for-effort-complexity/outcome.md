# Outcome — Accept L/M/H/VH shorthand aliases for --effort/--complexity

Work completed successfully.

## What changed

- **`tcw/store/base.py`** — added `WORK_LEVEL_ALIASES` and `normalize_work_level(value)`
  beside `WORK_LEVELS`. Pure/framework-free: lower-cases + strips input, passes
  canonical through, maps `l/m/h/vh` → canonical, else raises `ValueError` with a
  message listing the canonical values and the shorthand. No `argparse` import in
  the store layer (respects the abstract-spine boundary).
- **`tcw/work/cli.py`** — imports `normalize_work_level` (dropped the now-unused
  `WORK_LEVELS` import); adds a thin `_work_level()` argparse `type=` wrapper that
  re-raises `ValueError` as `argparse.ArgumentTypeError` so the message reaches the
  user cleanly. Swapped `choices=WORK_LEVELS` → `type=_work_level` on all four flag
  definitions (`new`/`edit` × `--effort`/`--complexity`); help text now advertises
  the L/M/H/VH shorthand.
- **Docs** — README quickstart comment, `skills/tcw-work/SKILL.md` estimates row,
  `docs/release-notes/upcoming.md` (Changed), `docs/changelogs/upcoming.md` (Changed,
  hash `6b86dbc`).
- **Capability** — `capabilities.yaml` records the `changed` back-pointer to
  `work#estimate-a-work-items-effort-and-complexity` (status stays Supported; body
  wording gets its small addition at the completion ledger flip).

## Verification performed

- `python -m pytest tests/` → **232 → 233 passed** (added 5 focused tests in
  `tests/test_work.py`: alias/case/passthrough, reject unknown+empty+whitespace,
  `new` stores canonical, `new` invalid exits with message, `edit` stores canonical).
- Live smoke:
  - `tcw work new "…" --effort h --complexity VH` → `show` reports `effort: high`,
    `complexity: very-high`.
  - `tcw work new "…" --effort s` → `error: argument --effort: invalid level 's';
    choose from low, medium, high, very-high (or shorthand L/M/H/VH)`.
  - `tcw work new --help` shows the shorthand in the flag help.
  - Smoke items dropped; no residue.
- `bllm-review-many` (2 models) run on the code diff. Applied: empty/whitespace
  reject assertions, an `edit`-path alias test. Dismissed: a false-positive
  "argparse not imported" (it is; smoke test confirms clean error), programmatic
  alias derivation (breaks `very-high`→`vh`), redundant direct-wrapper test.

## Deviations from plan.md

None material. The normalizer raises `ValueError` (not `argparse.ArgumentTypeError`)
in `base.py` to keep the store layer framework-free; the CLI wrapper does the
translation. This is a cleaner realization of the plan's "one source of truth"
intent than importing argparse into `base.py`.

## Follow-up notes

- None. The change is self-contained input sugar.

## Commits

- `5c1fbbd` planning artifacts · `e429668` start (active) · `6b86dbc` implementation
  + tests + docs · `4a57c0b` changelog.
