# Outcome — Install the plugin's CLI from PyPI instead of its own clone

`scripts/session_bootstrap.sh` now installs the published `tcw-cli` from PyPI
instead of `pipx install --force "$root"` against the plugin's own clone. The
version floats. There is no offline fallback, by decision. Everything else in the
change is documentation and capability wording.

## Commits

| Commit | Task |
| --- | --- |
| `853c68d` | Script + the two test assertions that pinned the clone |
| `a259d90` | Three capability records reworded |
| `da95e55` | Documentation Sync block: README, `tcw-plugin` skill + `setup.md` + `doctor.md`, `commands/tcw-doctor.md`, release notes, changelog — plus the doc-surface parser fix below |
| `1a85182` | Changelog entry for the parser fix |

## Acceptance criteria

| # | Criterion | Result |
| --- | --- | --- |
| 1 | Only install invocation is `pipx install --force tcw-cli` | ✅ `session_bootstrap.sh:101`, sole match |
| 2 | Exactly two assertions changed in `test_session_bootstrap.py` | ✅ diff confirms `:203` and `:215` only |
| 3 | Stale sentinel → records `install --force tcw-cli`, writes sentinel | ✅ `test_successful_install_writes_the_sentinel_then_goes_quiet` |
| 4 | Real editable checkout untouched | ✅ `test_real_editable_checkout_is_left_alone` |
| 5 | Failure → one line naming PyPI, stale sentinel, exit 0 | ✅ `session_bootstrap.sh:107`; `test_failed_install_prints_one_line_and_retries_next_time` |
| 6 | Steady state silent, no pipx | ✅ `test_steady_state_is_silent_and_never_calls_pipx` |
| 7 | Wide grep finds no stale clone-install prose | ✅ 3 hits, all inspected — each is a deliberate *negation* ("no longer installs from its own clone", "is **not** an install source", "no plugin-cache version to compare against"). One genuine leftover was found and fixed: the script's usage line said `[clone-root]`, now `[plugin-root]`. |
| 8 | `setup.md`, `doctor.md`, `commands/tcw-doctor.md` prescribe `tcw-cli` | ✅ every install/force-install/upgrade names `tcw-cli`; the `pipx`-absent ladder in `setup.md` installs `tcw-cli` too |
| 9 | No version-match promise; `sort -V` scan gone | ✅ `grep -c "sort -V" doctor.md` → 0; command `description` rewritten |
| 10 | All three capability deltas land | ✅ read back via `tcw capabilities show`; `tcw capabilities check` and `tcw validate` OK |
| 11 | README states the offline regression in the install section | ✅ a bolded paragraph directly under the plugin-install text, not only the changelog |
| 12 | Real-pipx migration re-run | ✅ see below |
| 13 | Full suite green | ✅ 1229 passed |
| 14 | Changelog + release notes name *this* change | ✅ both, including the network requirement |

## Criterion 12 — the migration, re-run

```
before: tcw-cli 0.20.1 | spec=/Users/brian/Projects/TCW
after:  tcw-cli 0.20.1 | spec=tcw-cli
venvs:  tcw-cli
tcw 0.20.1
```

One venv, `package_or_url` flipping from the local path to `tcw-cli`, working
binary. Existing plugin users migrate in place with nothing to clean up.

A first attempt ran the *script* rather than raw pipx and it correctly refused —
this machine has an editable dev checkout, which is `test_real_editable_checkout_is_left_alone`
firing for real. Worth recording: the guard the spec insisted must survive
demonstrably did.

## Deviation from the plan: one extra file changed

The plan and spec both asserted that `tests/test_session_bootstrap.py` would be
the only test file touched. **That prediction was wrong**, and the reason is a
latent bug rather than scope drift.

`tests/test_documented_cli_surface.py` parses `tcw` invocations out of backtick
spans with `\btcw\b`, which **matches inside `tcw-cli`** — `-` is a non-word
character. Once `setup.md`, `doctor.md`, and `commands/tcw-doctor.md` began
saying `pipx install --force tcw-cli`, the parser read those as `tcw` invocations
and reported `--force` as a nonexistent `tcw` flag. Three doc files failed.

The symptom fix would have been to reword the docs around the parser. The root
fix is four lines: require `tcw` to be followed by a space or tab before treating
a span as an invocation, and slice `_check` at the same anchor rather than at the
first literal `"tcw"`. Latent since the file was written; only reachable once a
doc named `tcw-cli` next to a flag.

**One wrong turn worth recording.** The first version of that fix used `\s`
instead of `[ \t]`. `\s` matches a newline, which let a span cross the line
breaks the `[^`\n]` character classes exist to forbid — and immediately produced
a *new* false positive: `skills/tcw-work/references/consolidate-plans.md` wraps
the phrase "there is no `tcw work consolidate-plans`" across a line, and the
looser regex reunited it and reported a sentence *denying* a verb as one
documenting it. Narrowed to `[ \t]`. A regression test covers the anchor
(`test_only_real_invocations_are_parsed`).

Still-latent limitation, deliberately not addressed: the parser cannot tell a
prescription from a negation on a single line either. Pre-existing, orthogonal,
and out of this item's scope.

## Notes

- Two open items for closeout: the repo split (the request's ask #2) as a
  follow-up item, and the version choice.
- The residual risk named in the plan stands: nothing here exercises a real
  harness session installing from PyPI end to end. Every layer beneath it is
  covered — argv assertion, real-pipx migration, live package — but the hook path
  itself runs only under an actual Claude/Codex session. That is what `verify`
  is for.
