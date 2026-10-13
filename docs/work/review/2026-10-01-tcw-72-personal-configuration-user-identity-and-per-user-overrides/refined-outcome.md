# Refined outcome — TCW-72: personal configuration

**Accepted** on 2026-10-13 under the TCW 3.0 epic's rule: a child item is
approved at verify when it passes a bounded adversarial review (the owner,
2026-10-02, restated 2026-10-13: "I'm going to do my own review and
verification after all slices are completed, not after each one"). The
confirming round ended `DONE`.

## What was accepted

Everything in `outcome.md`: one layered configuration loader (built-in, then
`tcw-config.yaml`, then the user-wide file, then `tcw-config.local.yaml`),
shared keys a personal file may not set, `inherit` in chain lists, origins for
every value, `TCW_CONFIG_DIR`, a user identity with `work list --mine` and
`--assign-me` in both backends, `validate` reporting every layer's problems and
a committed personal file, and `tcw config show [--origin]`. All 30 acceptance
criteria are met; `outcome.md` gives the evidence for each.

## Reviews

**Round 1** ran as two Claude reviewers (the loader, tasks 1–4; the commands
and records, tasks 5–7 and 9) and one bounded, read-only Codex run over
`tcw/config.py` and `tcw/config_cli.py`. Both Claude reviewers ended
`NOT DONE`; Codex found four defects, three of them the same as the Claude
reviewers'. The local model was not run. The fixes are in `outcome.md`'s
"Review fixes (2026-10-13)" section (branch `12a7c1c7..f8ec7f45`; spec notes
`a1b028d6`). The ones that mattered most:

- Delegating into a Jira-mode project applied the person's own files to the
  target, so a personal token variable could be sent to another project's
  site.
- `config show` printed a token pasted where a variable's name belongs.
- `inherit` was never resolved in a stage mapping no lower layer held
  (`completed`, `discarded`), so every command failed.
- A file that is not UTF-8 failed naming no file; `tcw serve` kept the
  configuration it read at startup; `validate` reported one bad file twice;
  `config show` output did not always read back as the same values.
- Jira being unreachable was reported as "no identity is configured".

**Three decisions taken in place of the owner** (each with a dated spec note):
`-env` values that do not look like a variable name are hidden in
`config show` (Design 8.4); `current_user()` returns nothing only when the
credential variables are unset, and otherwise raises as any Jira operation does
(Design 9.2, which settles a disagreement with TCW-71); the committed-file check
adds `--untracked-files=all` (Design 10.3).

**Narrowed, on evidence:** the doubled `validate` error came from the project
graph check, not the file scan; the committed-file check keeps `--ignored`,
without which an ignored file would be called committed. None rejected.

**Confirming round:** every finding reproduced against the unfixed code and
gone after the fixes, no regression, both narrowings correct, `DONE`. Its one
in-change note — the spec note and a record said every other Jira failure
exits 1, where it exits as for any Jira operation (a 404 is 4, a 5xx is 5) —
was corrected (`fe10d9b1`, branch `58da5913`).

Also carried on this branch: `0f1acf99`, a one-line TCW-73 follow-up (a
partial removal raised a bare `TcwError`, which TCW-73's own raise rule
forbids, so `tests/test_tree_store_raises.py` failed on the epic branch).

## Follow-ups

`docs/work/inbox/2026-10-13-tidy-what-tcw-72-s-reviews-left-for-personal-configuration.md`:
a list-valued YAML key crashing every command (older than TCW-72), an empty
mapping's origin when two layers write it, only the first bad credential key
reported, `new --stage inbox` reading piped input before its usage error, and
`!!binary` values written over several lines.

## Deferred, by the owner's instructions for this epic

- The full suite runs near the end of the epic. Here: the standing guard
  files, `tests/config/`, `tests/work/` and the files `outcome.md` names;
  `pytest --collect-only -q` collects 3899 tests cleanly.
- **This repository's own `tcw-config.yaml` is still 2.x.** Because every
  command now checks the whole configuration first, every `tcw` command run
  with the epic's code in this repository stops on it. TCW-76 migrates it;
  until then the board is driven with the installed 2.8.1.
- README, guides and skills go to TCW-74 and TCW-75; the migration guide to
  TCW-76; the viewer's `user` field to TCW-77.

## Capabilities

The records were written on the branch and pass the records gate there. They
reach `main`'s ledger only when the epic merges, so the item is completed by
hand, as TCW-69, 70, 71 and 73 were.

## Closeout route

The branch `work/2026-10-01-tcw-72-…` fast-forwards `epic/tcw-3.0`; its worktree
and branch are then removed. `main` receives 3.0 only when the epic ends. No
GitHub issue originated this item.
