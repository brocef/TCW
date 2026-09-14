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
