# Plan — Keep a reporter's private project details out of an upstream TCW report

Seven tasks. Task 1 is the ledger record; tasks 2–5 are the skill edit in the
order the file reads; tasks 6–7 close the capability and the documentation gate.
Nothing here compiles or runs, so every boundary is green by construction —
`tcw validate` and the suite are re-run at the end of each task anyway, because
the capability record and the item sidecar are both things `tcw validate` reads.

No blockers. `tcw work edit --blocked-by` is not used.

## Task 1 — Seed the capability record and the item's back-pointer

**Files:** `docs/capabilities/plugin/report-an-issue-upstream/meta.yaml` and
`description.md` (both created by the CLI); `capabilities.yaml` in this item's
folder (created by hand).

```sh
tcw capabilities add plugin/report-an-issue-upstream \
    "Report an issue or suggestion upstream" --status Missing
tcw capabilities set plugin/report-an-issue-upstream \
    --field "Planning doc=2026-09-10-keep-a-reporter-s-private-project-details-out-of-an-upstream-tcw-report"
```

Then write `description.md` in the voice of its two siblings
(`docs/capabilities/plugin/triage-github-issues/description.md`,
`.../run-a-post-mortem/description.md`) — a "As a user, I …" opening, then the
substance, then one harness line. It must describe the surface **as it will be
once this item lands**: feedback about TCW goes to the project's GitHub tracker
rather than the reporter's own `tcw work` store; the skill hands over a bug or
suggestion skeleton; and the report is written from a generic example mirroring
the reporter's setup, because the tracker is public and the project may not be —
as guidance, with the reporter deciding the contents. Close with the harness
line: there is no slash command, so Claude and Codex both invoke the
`tcw-report` skill directly.

Set `Subject:` to nothing. `triage-github-issues` carries no Subject either, and
`tcw taxonomy search issue` / `… search report` return no term to link.

Then create `capabilities.yaml` in the item folder:

```yaml
new:
    - plugin/report-an-issue-upstream
```

**Proof:** `tcw capabilities show plugin/report-an-issue-upstream` prints
`Status: Missing`, the minted `cap-` id, and the `Planning doc` back-pointer;
`tcw capabilities check` exits 0; `tcw validate` exits 0.

## Task 2 — Add the `## What goes in the report` section

**File:** `skills/tcw-report/SKILL.md` — new section between `## Before filing`
(ends line 29) and `## Bug skeleton` (line 31).

Covers design items 1, 2 and 5:

- Opens by saying these are guidelines and the reporter decides what the report
  contains.
- Two sentences on the asymmetry: the tracker at
  `https://github.com/brocef/TCW/issues` is public, the project being worked in
  may be private.
- The default: write a generic example that **mirrors** the setup.
- The swap list — repository, branch and directory names; node ids; work-item
  slugs; capability paths and wording; absolute paths; taxonomy terms and other
  domain vocabulary.
- The keep list — the command's shape and flags, the config's shape, the error
  type and message template, the sequence that triggered it, and the Environment
  block's real values (`tcw --version`, OS, install method).
- Verbatim output: say output from the generic reproduction is preferred, and
  that a reporter who wants to include output from their own system and
  environment may do so.

**Proof:** the section exists in that position and contains both lists; no
sentence in it instructs an agent to refuse, gate, or redact against the
reporter's wish (acceptance criteria 1, 2, 3, 7).

## Task 3 — Add the reproduction guidance to that section

**File:** `skills/tcw-report/SKILL.md` — a short block at the end of the section
added in task 2.

Covers design items 3 and 4: sketching the steps from a clean install and a
scratch project is worth doing and is **not** required to file; and the
reproduction can be handed to a subagent or an agent team member working in a
temporary directory, so nothing runs in the reporter's own checkout.

Word it so a Codex reader can act on it — no slash command, no Claude-only tool
name. Both harnesses have subagents, which is why the instruction can be given
outright (`docs/lifecycle/harness.md`;
`skills/tcw-work/references/procedures/delegation.md` is the in-repo precedent).

**Proof:** acceptance criteria 5 and 6 — the optionality sentence is present and
the delegation suggestion names no Claude-specific mechanism.

## Task 4 — Add the worked example and rewrite the closing paragraph

**File:** `skills/tcw-report/SKILL.md` — example inside the new section; closing
paragraph at lines 76–78.

The example is one identifying command or error and its mirrored form, at most
12 lines total, in a fenced block. It has to make the keep list visible: same
subcommand, same flags, same error type, different names.

The closing paragraph currently reads "Keep it concrete: a real command, a real
error, a real scenario beats an abstract description." Replace that sentence so
concreteness is located in the shape rather than in the identity — a real
command shape, a real error type, a real sequence, under names that are not the
reporter's. Keep the second half of the paragraph, the taxonomy / capabilities /
work axis hint, unchanged.

**Proof:** acceptance criteria 4 and 8 — the example is present and within
budget; `grep -n "beats an abstract description" skills/tcw-report/SKILL.md`
returns nothing; the axis hint still resolves.

## Task 5 — Re-phrase the skeleton placeholders, and confirm the untouched surface

**File:** `skills/tcw-report/SKILL.md` — bug skeleton lines 44 and 51.

Design item 7: `<exact command or action>` and `<what happened — paste the error
/ output verbatim>` gain the mirrored framing, so the skeleton stops
contradicting the section added in task 2. The Environment block (lines 36–40)
and the `tcw --version` step (lines 28–29) are not touched.

Then confirm design item 8 in the same pass: `allowed-tools` at line 5 is
byte-identical, the file contains no command that posts to GitHub, and
`wc -l skills/tcw-report/SKILL.md` is under 120.

**Proof:** acceptance criterion 8, plus
`git diff -- skills/tcw-report/SKILL.md | grep '^[-+]allowed-tools'` returning
nothing.

## Task 6 — Flip the capability to Supported

**File:** `docs/capabilities/plugin/report-an-issue-upstream/meta.yaml`.

```sh
tcw capabilities set plugin/report-an-issue-upstream --status Supported
```

Run it only after tasks 2–5 have landed — the record then describes something
true. The completion gate refuses `complete` while a `new:` path still reads
`Missing`, so this is also what unblocks the transition.

**Proof:** acceptance criterion 9 — `tcw capabilities show` reads `Supported`,
`tcw capabilities check` exits 0, `tcw validate` exits 0.

## Documentation Sync

Evaluated as one block after tasks 1–6, over the finished diff. All four of this
project's entries are considered; two fire.

| Entry                                        | Trigger                  | Verdict                                                                                                                                                                                                                                                                                        |
| -------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/changelogs/upcoming.md`                 | `Any-Code-Change`        | **Fires.** One `Changed` line for the report skill's disclosure guidance, one `Added` line for the `plugin/report-an-issue-upstream` capability record.                                                                                                                                          |
| `docs/release-notes/upcoming.md`              | `Public-API`             | **Fires.** One plain-language line: reports filed upstream now start from a generic example that mirrors your setup, so a private project's names stay out of a public issue. No module names, no capability paths.                                                                              |
| `README.md`                                   | `Public-API`             | **Evaluate; expected no change.** Line 279's `tcw-report` row — "Reporting a `tcw` bug or suggestion upstream to this project's issues" — is still accurate after this change. Re-read it against the finished skill and edit only if it has become wrong; record the decision either way.        |
| `skills/<component>/SKILL.md`                 | `Skill-Driven-Component` | **Evaluate.** The changed component *is* a skill, so there is no second skill driving it — but `skills/tcw-plugin/SKILL.md:29-31` describes `tcw-report` to a routing reader ("with a ready-to-fill skeleton"). Decide whether that sentence should mention the generic-example default; keep it to one clause if so. |

## Verification

**Commands** (all run from the repository root):

- `tcw validate` — exits 0.
- `tcw capabilities check` — exits 0.
- `/usr/local/bin/python -m pytest tests/test_plugin_manifests.py -q` — 19 pass.
- `/usr/local/bin/python -m pytest -q` — full suite, before `submit`.
- `wc -l skills/tcw-report/SKILL.md` — under 120.
- `grep -n "beats an abstract description" skills/tcw-report/SKILL.md` — no match.

> Environment note for this container: the `pytest` on `PATH` is a `uv` tool
> install that cannot see the project's dependencies and fails collection with
> `No module named 'yaml'`. `/usr/local/bin/python -m pytest` is the interpreter
> that has them. `scripts/remote_session_setup.sh --force` does not fix the
> `PATH` copy.

**What the suite cannot check.** Acceptance criteria 1–8 are reads of the
finished file; nothing in the tree can falsify them, for the reason recorded in
the spec's `## Notes`. At `verify`, read `skills/tcw-report/SKILL.md` end to end
and check:

1. The new section sits between `## Before filing` and `## Bug skeleton`, and
   opens on guidance rather than instruction (criteria 1, 2).
2. No sentence in the file tells an agent to refuse a report, hold it for
   approval, or redact against the reporter's stated wish (criterion 2). This is
   the criterion most likely to be violated by an otherwise good section — read
   for it specifically.
3. Both lists are present and the Environment values are on the keep side
   (criterion 3).
4. The example is at most 12 lines and a reader could apply it to their own case
   (criterion 4).
5. The fresh-environment steps and the delegation suggestion are both marked
   optional, and neither names a Claude-only mechanism (criteria 5, 6).
6. The verbatim-output sentence states a preference and leaves the choice
   (criterion 7).
7. The closing paragraph still argues for concreteness, and the axis hint
   survives (criterion 8).

**Read as a Codex user would.** The skill ships to both harnesses; anything that
only makes sense with a Claude slash command or a Claude tool name is a defect
found by reading, not by the suite.

## Notes

- Tasks 2–5 all touch one file in sequence. They stay separate because each maps
  to a distinct set of acceptance criteria and the file's own reading order makes
  the sequence natural; commit them separately, per this repo's stage-artifact
  discipline.
- The capability record is seeded `Missing` in task 1 and flipped in task 6 with
  the skill edit in between, so the ledger never claims the guidance exists
  before it does.
