# Outcome — Audit the backlog and upstream issues against the new lifecycle

Four plan tasks. **Eleven backlog items and one GitHub issue audited; two items
rescoped, nine untouched, three new items filed.** Nothing tracked changed before
the requester approved.

## Task 1 — the audit (read-only)

Dispatched to three `tcw:tcw-backlog-auditor` agents, grouped by subject rather
than one agent per item. **A deviation from the plan, recorded rather than
silent**: the agent's definition scopes it to one item, and eleven separate
dispatches was not a good trade. The load-bearing property — reports, never
edits or transitions — was preserved, and the coordinating session re-verified
every claim it acted on.

The fourth group (issue #12 and the three carried-forward defects) was audited
by the coordinating session directly, which already held the context.

### Dispositions

| Item | Disposition |
| --- | --- |
| `2026-08-04-…external-tracker-bridge` | **rescoped** — two passages |
| `2026-07-22-…eval-harness` | **rescoped** — three areas across request, spec, and plan |
| `2026-06-19-remote-adapter-jiraworkstore` | unaffected |
| `2026-06-19-remote-extends-for-taxonomy` | unaffected |
| `2026-06-19-tracker-sync-for-capabilities` | unaffected |
| `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source` | unaffected |
| `2026-08-11-accept-comma-separated-tags-on-tcw-work-new` | unaffected |
| `2026-07-30-validate-capability-subject-and-feature-refs-at-write-time` | unaffected |
| `2026-07-30-fix-non-git-write-paths-…` | unaffected |
| `2026-07-30-resolve-taxonomy-refs-against-symlinks-…` | unaffected |
| `2026-07-02-add-a-vendored-rich-markdown-editor-…` | unaffected |
| GitHub issue **#12** | unaffected — see below |

**Nine of twelve unaffected is the finding, not a failure to find anything.** The
epic changed the work axis; it changed zero lines of `tcw/taxonomy` and
`tcw/capabilities` (`git diff --stat main...HEAD` over both is empty), which is
where four of the untouched items live.

Evidence for the ones most likely to have moved, re-verified by the coordinating
session rather than taken on report:

- **`validate-capability-refs`** — still exactly true. `_validate_fields`
  (`tcw/store/fs.py`) checks field *names* and `Status` values and never refs;
  resolution lives in `check` (`_check_subject` `fs.py:1851`, `_check_feature`
  `:1864`). C7's four `--field` writes are a fresh instance of the gap: they
  succeeded only because the refs happened to be valid.
- **`accept-comma-separated-tags`** — `tcw/work/cli.py:1334` declares `--tag`
  (`action="append"`) and no `--tags`. C1 changed what `new` *writes*, not how it
  parses.
- **`remote-extends-for-taxonomy`** / **`tracker-sync-for-capabilities`** — their
  axes are untouched. `Tracker` is still recognized-but-unparsed at
  `tcw/store/base.py:312`, its only occurrence in the Python source.

## Task 2 — one table, then stop

Presented as a single approval pass, per the requester's amendment to the epic
plan's one-item-at-a-time rule. **No `tcw work` transition, edit, or `gh` write
occurred before the answer.** That is criterion 3, and it was discharged by not
acting.

## Task 3 — executed exactly what was approved

**Rescope 1 — `2026-08-04-…external-tracker-bridge`** (`d08c034`). Its import
step wrote a ticket snapshot into `initial-request.md`. A tracker snapshot is
raw unprocessed input — intake by definition — and writing it to the request
lights the board's `R` for an item nobody has written up, which is the defect C1
closed. Now writes intake and lets the `request` stage promote it. Second
passage: `tcw work show --json` is a closed versioned document
(`tcw/work/projection.py`), so surfacing tracker state there is an explicit
modelling decision, not a free-form addition.

**Rescope 2 — `2026-07-22-…eval-harness`** (`9949b04`). Three things were false.
Its non-goals excluded CLI changes because "mechanism stays in the binary" — but
since C6 the *judgment layer* ships inside the binary, so a prompt edit is
in-scope prose that ships in the wheel and earns a release note. Its baseline arm
moved: `tcw --help` now reaches the full methodology in **both** arms, so the
with/without-skill delta measures what the skill adds *beyond* the prompts, and a
near-zero early delta is informative rather than damning. And the seam C7's
refined outcome conceded no test can reach — whether a 22-line router faithfully
fronts a 40-line prompt — is now the most interesting thing the harness can
measure. Also corrected a stale claim that the README omits `tcw-post-mortem`
from its skill catalog; `README.md:111-113` lists it.

Both rescopes stayed inside the bound the spec set: correcting what an item
*means* against the new model, not redesigning it.

**Three new items filed** (`01ef766`), each carrying the evidence:

| Slug | Priority |
| --- | --- |
| `2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule` | 35 |
| `2026-08-18-close-the-readme-lifecycle-heading-…` | 25 |
| `2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-…` | 20 |

**Nothing was discarded.** The epic plan predicted two discards and named both;
**both already read `completed`** — resolved by other means while the epic ran.
Recorded per criterion 7 rather than acted on.

**GitHub issue #12** — verified still live against current HEAD:
`_hosted_projects()` (`tcw/serve/__init__.py:415-427`) returns `set()` without
descendants and descendants-only with, so the anchor's own project id is in
neither. Unrelated to this epic. **The requester chose to skip it for now** —
left open, no comment posted, no work item filed. Deliberately deferred, not
overlooked.

## Task 4 — whole-tree checks

```
1580 passed in 279.68s (0:04:39)
validate OK
capabilities OK
no capability drift
```

C7's capability sweep was **not** repeated, per the spec: it found one falsified
record and two linkage gaps and fixed all three.

## What the plan and spec got wrong

**One thing, and it is the plan's own mechanism.** Task 1 says "dispatched to the
`tcw:tcw-backlog-auditor` agent", which is scoped to one item. Grouping eleven
items into three dispatches was the right trade but is not what the plan says;
recorded above rather than glossed.

Otherwise both held. The spec's addition of a fourth disposition — **unaffected**
— earned itself immediately: nine of twelve, and without it every item would have
had to be forced into a change.

## Notes

- **The epic overestimated its own disruption, in the safe direction.** Its plan
  named two likely discards (both already complete) and predicted the three
  `remote/*` items would "inherit an abstract intake surface and a versioned
  DTO". Two of those three sit on axes the epic changed zero lines of. A forecast
  written at planning time about a design not yet built, and wrong in the way
  that costs nothing.
- **One contingent seam, noted not filed.** The tracker-bridge item specifies
  provider registration and credentials under `work.tracker`;
  `2026-06-19-tracker-sync-for-capabilities` calls for "provider configuration,
  authentication, and permission boundaries" against what would be the same
  tracker. If the bridge ships first, edit the capabilities item to reuse that
  layer rather than define a second. Nothing to point at yet.
- **`2026-08-11-accept-comma-separated-tags`'s open question is already
  answered**, for whoever specs it: completed item
  `2026-07-23-blocker-refs-comma-split-mangles-external-text-…` removed
  comma-splitting from `--blocked-by` *as a bug*, because external blocker text
  may contain a comma. Generalizing would reintroduce a fixed defect. Tags are
  safe because `_tag` normalizes to a slug, so the sugar belongs on `--tag` only.
- **No local LLM tooling was used**, per the requester's instruction.
