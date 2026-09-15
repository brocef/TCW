## Inbox manifest

- `2026-09-14-eval-runs-under-this-checkout-grade-and-behave-wrongly.md`

## Inbox body

# Eval runs under this checkout grade and behave wrongly

Found by the adversarial review of
`2026-09-14-make-eval-checks-measure-what-the-agent-did-…`. All four existed
before that item and are outside its scope.

1. **The fixture path is doubled when a default run is graded.** `run_one`
   (`evals/run_evals.py`) writes `"fixture": str(out / "fixture")`, and with the
   default `--out` (`eval-runs/iteration-1`) that path is relative.
   `grade_run` (`evals/grade.py`) joins it onto the run directory, so
   `python -m evals.grade eval-runs/iteration-1` looks for
   `eval-runs/iteration-1/B10/with-skill/eval-runs/iteration-1/B10/with-skill/fixture`.
   The comment "A live run writes an absolute path" is false for the default.
   Every check that reads the fixture is affected. Confirmed by reading the code;
   not run.
2. **Fixtures seeded inside this checkout sit under TCW's own project.** `tcw`
   finds `tcw-config.yaml` in parent folders, and Claude Code may load this
   repository's `CLAUDE.md`/`AGENTS.md` from parent folders too, in every arm.
   The bare fixture now refuses to seed inside a TCW project; the control and
   customized fixtures have their own config, but the instruction-file question
   is unverified.
3. **`manifest.json` sits in the agent's working folder and holds the axis A
   nonces.** It is now hidden from git through `.git/info/exclude`, but an agent
   can still read it and copy a nonce into an artifact. Writing it beside the
   fixture instead would remove both problems.
4. **Case B10's prompt describes a fix that is not in the fixture.** It says the
   user fixed an off-by-one in CSV export in `src/reports.py`; that file has no
   CSV export, and nothing is changed. An agent that checks `git diff` finds
   nothing to document. Committing the described fix as the seeder's last commit
   would make the prompt true. Also open: whether a bug fix that restores
   existing behaviour should fire `README.md`'s `Public-API` trigger at all.
5. **`run_one` never writes `items` to `timing.json`.** Its entry carries
   `nonces` and `stage_items` but not `items`, while `grade_run` reads
   `timing.get("items", {})`. So on a real run `item_status` and
   `new_item_count` read an empty mapping and grade wrongly. The committed
   grading fixtures under `tests/fixtures/eval_grading/` do contain `items`,
   which is why no test notices. Confirmed by reading the code (verification
   round 1 of the eval checks item).
6. **Check what `claude -p` itself writes into the fixture.**
   `files_changed_exactly` now counts every untracked file that isn't ignored,
   so anything the harness writes into its working folder is charged to every
   run. The first paid run should list `git status --porcelain --ignored` for one
   fixture and exclude whatever the harness, rather than the agent, left there.
7. **Reusing an `--out` folder can still stop a paid run partway.** `seed()`
   now refuses a fixture folder that is not empty, but `run_evals.main()` only
   checks bare arms up front. A run with `--axis b --out X`, after an earlier
   `--case B11 --out X`, spawns the new arms and then raises when it reaches
   B11's used folder. Moving the "fixture folder must be new or empty" check into
   the same up-front loop for every arm would stop it before anything runs.
   Found by both reviewers in verification round 2 of the eval checks item.

## Widened at triage (2026-09-15)

Two eval harness gaps from the skill restructure review were folded into this item
rather than opened as their own, because they are defects in the same harness
(`evals/coverage.py`, `tests/test_eval_coverage.py`, and cases B4 and B8).

## Folded in: from inbox entry `2026-09-14-guards-and-gaps-the-skill-restructure-review-left.md` (Guards and gaps the skill restructure's review left for separate changes)

2. **Nothing checks that `EXCLUSIONS` and `PARTIAL` in `evals/coverage.py` name
   skills that still ship.** A stale key (say a deleted skill) passes
   `tests/test_eval_coverage.py`.

6. **B4 and B8 only catch a wrong route into `tcw-setup`.** Each asserts
   `tool_input_absent` `tcw-setup/references/`, as the spec asked. A B8 run ("Set
   it up.") that opened a `tcw-configure` document instead passes every mechanized
   check, although "set it up" there asks for a term, a capability and a work item,
   not a configuration change. This is a gap in the spec, not a departure from it;
   adding `tool_input_absent` `tcw-configure/references/` to both cases would close it.
