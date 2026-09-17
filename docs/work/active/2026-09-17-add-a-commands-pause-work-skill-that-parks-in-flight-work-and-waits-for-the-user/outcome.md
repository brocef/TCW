# Outcome: commands-pause-work

Shipped as specified, on `claude/adoring-knuth-j8yy20`. No file under `tcw/`
changed — `git diff --stat origin/main...HEAD -- tcw/` is empty, which was the
request's hard constraint and is checked by nothing else.

## What shipped

| Task | Commit | What |
| --- | --- | --- |
| 1 | `a12092a` | Taxonomy Feature `commands-pause-work-skill` (vocab: `skill`, `work-item/lifecycle-stage`) |
| 2 | `0d26ed3` | Capability `skills/commands-pause-work`, seeded `Missing`, with `Feature`, `Subject` and `Planning doc`; the item's `capabilities.yaml` |
| 3 | `2c319d0` | `skills/commands-pause-work/SKILL.md`, plus the verdict row, Codex manifest and eval exclusion that must land with it |
| 4 | `5d64a1f` | The resume-side read: `skills/work/SKILL.md` "Finding your place" and a pointer from `commands-drive-work-to-completion` |
| 5 | `5527bcb` | The two prose enumerations — `commands.md` and `README.md` |
| 6 | — | The tolerance probe; no permanent change (see below) |
| 7 | `ed81615` | Release note and changelog entries, and the two counts this change makes stale |
| — | `b7cf520` | Fix: the skill named `tcw work discard`, which is not a command |

Also `637ee40` / `47a6e08`: a real handoff written, committed, pushed, read back
and deleted, as the plan's end-to-end verification (below).

## Test result

`python -m pytest` — **3609 passed, 2 skipped** (547s). `tcw validate` exits 0,
with and without a handoff file present in an item folder.

The three registration tests were **mutation-checked, not just run**. Reverting
each of `skills/README.md`, `.codex-plugin/plugin.json` and `evals/coverage.py`
in turn made exactly the expected test fail, each naming the real defect:

- `every shipped skill … needs exactly one verdict row …: ['skills/commands-pause-work/SKILL.md: 0 rows']`
- `the Codex description does not say 'seventeen skills' for the 17 that ship`
- `these skills ship but no eval case invokes them and no exclusion accounts for them: commands-pause-work`

That confirms the plan's central sequencing claim — the skill file and its three
registrations had to be one commit — rather than assuming it.

## Verification

1. **Nothing under `tcw/`** — confirmed, empty diff.
2. **Suite green, `tcw validate` 0** — above.
3. **`when_to_use` triggering** — fires on pause / stop for now / hold off /
   stand down / losing connection / reboot / another machine; explicitly excludes
   finishing, abandoning and blocking. Reading this is what caught the
   `discard`/`drop` defect.
4. **Codex-safe** — no dynamic context injection, no `$ARGUMENTS`, no `agents/`
   dispatch; every instruction is `tcw` plus git. Grepped, not assumed.
5. **The eval exclusion reason is its own**, not the four-skill copy. Checked by
   reading, because `tests/test_eval_coverage.py` tests key presence only and
   cannot see this.
6. **The reworded `commands.md` sentence is true of all five** — the old one
   claimed each invokes `work-stage` for the stage it runs, which this skill does
   not.
7. **End-to-end, done for real on this item.** Wrote `implement.handoff.md`,
   committed and pushed it, read it back, confirmed it answered where the work
   stood / on which branch / what next, then deleted it in the same step and
   committed the deletion. `tcw validate` stayed green throughout.
8. **The push reached the remote** — `git log origin/claude/adoring-knuth-j8yy20`
   showed both the work commit and the handoff commit. This is the exact defect
   the first spec shipped, so it was checked rather than trusted.

## Task 6: what the probe actually proved

The spec's survival claim held, and better than claimed. An unregistered
`implement.handoff.md` rode **two** transitions — `backlog → active` and
`active → discarded` — with its content intact, and `tcw validate`, `tcw work show`
and `tcw work list` reported the item no differently with it present.

Residue, corrected after verification: the probe folder sits in
`docs/work/discarded/`, which `.gitignore:29` makes **untracked** — so it is local
to this machine and does not travel with the branch. The only thing that ships is
one line in `docs/work/graveyard.yaml` recording the slug as `wontfix`. An earlier
draft of this section reasoned about retention policy as though the folder merged;
it does not. `tcw work delete` does decline it (`work.retain.discarded` keeps
resolved items), but that decides only what stays on this disk.

## What verification found

An independent verifier pass over the 16 acceptance criteria returned 15 met and
one partially not met, plus three defects outside the criteria. All were fixed
before the accept decision rather than deferred:

1. **Criterion 7's resume-and-delete statement was missing from the skill body.**
   The behaviour existed in `skills/work/SKILL.md`, but the pause skill never told
   its reader the file would be deleted on resume — so a pausing agent could not
   say what would happen to the document it had just written. Added.
2. **`when_to_use` named `tcw work drop` for abandoning**, and `drop` refuses any
   item not in `backlog` (`tcw/store/base.py:3556`). A pause during `implement` is
   by this skill's own table an `active` item, so the reader most likely to follow
   that clause would hit an error. This is the *third* instance of the same shape
   — the commit that fixed `discard`→`drop` introduced it, and the outcome section
   below recorded discovering that `drop` cannot reach an active item without
   revisiting the line it had just written. The command name is now gone from that
   negative clause entirely, which is the root fix: naming a command in a
   "not for this" aside carries no value and is what kept biting.
3. **`commands-verify-work` never routed through "Finding your place"**, going
   straight to `work-stage verify`. A `verify`-stage pause resumed with the skill
   named for that stage would leave the handoff unread — while the release note
   promised "the agent reads it and deletes it". The pointer was added there too.
4. **`outcome.md` described the probe residue inaccurately** (above), and
   `commands-drive-work-to-completion` overstated the router's ordering. Both
   corrected. A README table cell was also one character short of its neighbours.

The verifier also caught that this document's mutation-check quote was a
paraphrase presented as command output, and that two tests fail on that revert
rather than one. Recorded rather than quietly reworded: the substance held, the
transcription did not.

## What the plan and spec got wrong

Four things, all found by running the plan rather than reading it.

1. **The plan named a command that does not exist.** Task 6 said
   `tcw work discard`; the CLI verb is `tcw work drop`, and `discard` is only the
   transition id. The same error had reached the shipped skill's `when_to_use`,
   where it would have told users to type a command that errors out — fixed in
   `b7cf520`. Worth noting that the plan's own citation-checking pass did not
   catch it, because it verified `file:line` references and not command names.
2. **The plan was wrong that no test constrains `skills/work/SKILL.md`'s length.**
   It does: `test_the_router_stays_within_its_line_budget` caps the body at 60
   lines and the file was at 59. This is a correction of a correction — an earlier
   draft cited `ROUTER_LINE_CEILING`, which really does apply only to
   `stage-<id>.md`, and I replaced a right-for-the-wrong-reason claim with a wrong
   one. The budget's stated rule is "extract, never grow", so the handoff sentence
   was folded into an existing line and the body is still 59.
3. **`tcw work drop` cannot reach an active item** — only `backlog`. Task 6's
   cleanup assumed otherwise; the probe had to be completed with
   `--resolution wontfix` instead, which is what produced the second transition
   the survival claim got tested against. An accident that improved the evidence.
4. **A JSON round-trip reformats more than it edits.** Rewriting
   `.codex-plugin/plugin.json` through `json.dumps` expanded an unrelated inline
   array into three lines. Reverted, so the committed diff is the one line it
   should be. Nothing broke; it would have been review noise.

## Notes

- `work.retain.discarded` keeping the probe is the honest reason the board now
  carries a spent scratch item. If that is unwanted, the fix is a policy decision,
  not a hand deletion.
- The follow-up named in the spec — registering `handoff` in `WORK_SIDECARS` so
  `tcw` can see, validate and display it — is still not filed, on the spec's
  reasoning that it is better judged after the convention has been used. The
  end-to-end run above is one use, not enough to judge on.
