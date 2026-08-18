# Outcome — Repoint the work skill and docs at the CLI

Seven commits, in the plan's order, plus this one. **Implemented across three
sessions**: an agent completed tasks 1–3 and died on a session limit, a second
completed 4–5 and died the same way, and the coordinating session finished 6–8.
Each handover recovered from the tree rather than from a report, which is the
property the per-task commits exist to give.

## What shipped

### 1. The self-review pass in three shipped prompts — `ea937c8`

`tcw/work/prompts/{spec,plan,implement}.md`, plus
`test_the_self_review_pass_appears_in_exactly_three_prompts` in
`tests/test_shipped_prompts.py`. `spec.md` gets a `## Self-review` heading with
three items — a `file:line` citation re-resolves to what it claims, every
criterion executable against the tree today has been executed, and a criterion
two readers could check two ways is pinned to one reading. `plan.md` and
`implement.md` fold theirs into existing steps under a `**Self-review.**` lead,
which is the detection token the set-equality test greps for.

**The escalation did not fire.** The block fit in 8 lines and `spec.md` landed at
exactly 48, its cap. No existing prompt content was compressed to make room.
— criteria 5, 6, 7

### 2. Six routers, and the four tests that bound them — `9d90181`

`stage-{request,spec,plan,implement,verify,postmortem}.md` reduced against the
spec's §5 table, in one commit because the four parity assertions are
parametrized over the same six ids and a per-document commit would be red at
five of six boundaries. Two assertions changed (the harness-neutral command is
now `tcw work stage <id>`; four sections instead of five, `inbox` keeping its
fifth) and three added (the shared-sentence check, the 40-line ceiling, and the
judgment-survives check). `stage-inbox.md` was not opened.
— criteria 1, 2, 3, 4

### 3. `SKILL.md` — `1fe88dd`

The "Always" bullet named `tcw work lifecycle --stage`, which reports bindings
and never resolves a `builtin`; on a node configuring nothing it reports
nothing, so an agent following the router literally never reached the prompt C6
shipped. Now `tcw work stage <id> <slug>` — `slug` required, not the optional
`[ref]` the epic's prose implied. The stage/artifact table's `Runs in` column
restated `STAGE_STATUSES`, which the verb enforces and names in its own refusal;
dropped. Net zero lines: the body is at 60 of 60.
— criterion 9

### 4. `hooks.md` consolidated — `4dd2d2e`

159 → **92 lines**. Nothing in it was false; three children each appended a
correct section, and the defect was duplication against `README.md:605-735` and
against `tcw work stage --help` / `tcw work scaffold --help`. The role × kind
table is kept in full. Verification output, per the plan:

```
92 skills/tcw-work/references/hooks.md
never executed       1
fail closed          1
runs no hooks        1
not a sandbox        1
| `check`            1
| `prompt`           1
| `artifact`         1
```

— criterion 8

### 5. Documentation Sync — `b25a15d`

One pass over the finished diff. `README.md` §605-735 consolidated — every hunk
falls between `:636` and `:719`, so no line outside the bounds moved; C5's and
C6's corrections are preserved rather than undone. Release notes gain one plain
section on the self-review pass; `:161-176` untouched. Changelog gains the
*Changed* entries. The `skills/<component>/SKILL.md` trigger fires and is
**already discharged by tasks 2–4** — the skill is the item — recorded rather
than double-counted.
— criteria 10, 14

### 6. The capability record's one false line — `25a7a58`

`work/configure-the-work-lifecycle`'s line 6 promised that everything configured
before still works and prints the same thing, and that a stage id with a plain
list means what it always meant. Both are false for exactly one plain list — the
empty one. Replaced with wording taken from the release notes rather than
invented, naming the `tcw validate` refusal and the `{blob: ""}` opt-out.
`Status` stays `Supported`. The four archive hits elsewhere that quote the
sentence to *name* it as the contradiction are true historical statements and
were not edited.
— criterion 11

### 7. The four linkage fixes — `84553f7`

Fields, not prose, and a separate commit. `run-a-lifecycle-stage` had no
`Subject` at all; the `configurable-work-lifecycle` Feature had zero inbound
references while nine other `work/` records carry one; and
`configure-the-work-lifecycle` — the record *about* hooks — lacked the
`work-item/lifecycle-hook` term C3 added for that noun.
— criterion 12

### 8. Whole-tree checks — no commit

```
1580 passed in 272.61s (0:04:32)
capabilities OK
no capability drift
validate OK
```

`git diff b2f65de~1..HEAD -- skills/tcw-work/references/stage-inbox.md` is
empty — criterion 1's byte-identity clause.
— criterion 13

## Final sizes

Routers (ceiling 40, no floor): request 23, spec 28, plan 30, implement 29,
verify 36, postmortem 22. `stage-inbox.md` unchanged at 67.

Prompts (ceiling 50): request 39, spec **48**, plan 41, implement 40, verify 40,
postmortem 40.

## What the plan and spec got wrong

**Nothing material.** The two numeric tensions the plan flagged both resolved as
it predicted:

1. **The 8-vs-10 line budget.** Spec §4 said "hard budget of 10 lines" while
   criterion 6 capped `spec.md` at 48 — from a 40-line file those are different
   numbers. The plan took 8, the tighter one, and 8 was enough.
2. **Five of six routers land well under 40**, exactly as spec §5 computed. The
   requester had already amended constraint 1's 40–50 range to a ceiling with no
   floor on the strength of that arithmetic, so this is the design working, not a
   miss.

## Notes

- **The `## Exit` removal is one-directional.** Arguing "how does this stage end
  well" back into a router now means arguing against a test. That is intended
  (spec §Risks) and is recorded so the argument is available rather than
  rediscovered.
- **A faithful paraphrase inside 40 lines is still uncaught.** Criterion 2
  catches a copied sentence; nothing catches a router restating its prompt in
  different words, and C7 wrote both sides. The 40-line ceiling is the backstop —
  a router that paraphrased its whole prompt would not fit — but a single
  paraphrased paragraph inside budget would survive. This is the item's main
  verification-stage question, along with whether the rewritten README section
  states each of its four facts exactly once.
- **Carried to C8, untouched here**: `hooks.md`'s "configured-but-missing skill"
  note, which would be better said by `tcw work lifecycle` than by the skill but
  is a CLI change; `README.md`'s heading at `:605` having no closing boundary, so
  everything to `:1017` renders inside it; and `read_artifact`'s `p.is_file()`
  (`tcw/store/fs.py:3478`) still disagreeing with the canonical presence rule.
