# Outcome — Serve documentation-sync entries from tcw-config.yaml instead of scraping the agent guide

Documentation entries are configuration now. `tcw validate` checks them,
`tcw work docs` prints them, and `tcw work stage plan|implement` put them in
front of the agent instead of telling it to go and find a Markdown heading. A
project that declares nothing sees **byte-identical** output, proven against a
fixture captured before any prompt was touched.

Suite: **1691 passed, 0 failed in 266s** — against the spec's floor of 1592.

## What shipped, task by task

| # | Task | Commit |
| - | ---- | ------ |
| 1 | Fallback baseline captured **before** any prompt was edited | `8575993` |
| 2 | `DocEntry` + `parse_documentation_entries` | `0f4afe6` |
| 3 | `WorkStore.documentation()` + `tcw validate` | `cc20a4a` |
| 4+5 | Render, substitute, and `tcw work docs` | `ebc387a` |
| 7 | This repository migrated | `2aef50f` |
| 6 | Skill and references repointed | `99ee689` |
| 8 | Migration guide rewritten | `e7a11c2` |
| 9 | README, release notes, changelog, `tcw-work` skill | `591a195` |

Tasks 4 and 5 landed as one commit: both edit `tcw/work/cli.py`, and splitting
them needed a partial commit. The plan's ordering constraint — a green suite at
every boundary — is unaffected.

## Acceptance criteria

Twelve of fourteen met as written, one exceeded, **one deliberately not met**.

- **1, 2** — `tests/test_documentation_config.py`, 33 cases, at the parser and
  again at the `tcw validate` boundary.
- **3** — `tests/test_prompt_fallback.py` replays a fixture captured in commit
  `8575993`, before `resolve.py` or either prompt was touched.
- **4, 7a, 7b, 8, 9** — `tests/test_documentation_prompt.py`, 31 cases. Prompt
  line counts stayed within the ceiling; `tests/fixtures/lifecycle_baseline/`
  passed **without re-capture**, as criterion 9 predicted.
- **5, 6, 7** — `tcw work docs` and `--json`; criterion 7 by hashing every path
  under the node before and after both invocations.
- **10, 11a, 12** — skill, references, migration guide.
- **13** — 1691 passed against a floor of 1592.
- **11 — not met as written, deliberately.** See below.

### Criterion 11 was wrong, and the code is right

It required that "this repository's `AGENTS.md` has **no** `## Documentation
Sync` section". The section is still there. What left it is the **entry list**;
what stayed is the directive to invoke the skill and the reasoning for why these
four documents exist.

Removing the whole section would have been a mistake for two reasons found while
doing it. The skill's own `references/setup.md` says to "**always** include the
opening directive line… without it, future sessions may see the file list but
skip the trigger-evaluation logic" — that directive is not an entry and has
nowhere else to live. And the item's own premise is *config carries the facts,
the guide carries the reasoning*; deleting the reasoning would have overshot it.

The criterion should have said "no longer enumerates the entries", which is what
`test_the_agent_guide_no_longer_carries_the_entry_list` asserts and what the
section now satisfies.

## What the plan or spec got wrong

**1. The spec's core mechanism could not work as designed.** It specified one
placeholder, `{{tcw:documentation}}`, resolving to "the exact sentence those
prompts carry today" held as a fallback in Python. The two prompts do not carry
the same sentence — `plan` says "and name a task for each trigger that will
fire", `implement` says "once, against the whole finished diff rather than the
task you just committed" — so **one constant cannot reproduce both byte-for-byte**,
and criterion 3 is the criterion the whole item turns on.

The token became a span carrying its own fallback:

```
{{tcw:documentation}}…the original sentence, unchanged…{{/tcw:documentation}}
```

With entries configured, the span becomes the rendered list. With none, it
becomes its own inner text. Byte-identity holds **by construction** rather than
by a Python constant somebody has to keep in agreement with a Markdown file, and
the prose stays where prompt prose belongs. Everything else the spec decided
about substitution — that it happens in `resolve_prompts` over the joined text,
never in `_resolve_one` — was right and is unchanged.

**2. The spec predicted the prompts would get one line shorter.** "41 → 40 and
40 → 39 against a ceiling of 50." They did not: both are unchanged at 41 and 40,
because a span keeps the text it wraps. Harmless, and the ceiling test passes
either way, but the prediction was wrong.

**3. A rendering bug that was a correctness issue, not cosmetics.** The prose
following a substituted span landed at **four spaces** after a Markdown list,
which CommonMark reads as a *code block*. Found by doing what the plan's
Verification step 2 asked — reading the resolved output and judging it, which no
test had been written for. Fixed by trimming the separator space, and now pinned
by `test_text_after_the_span_resumes_at_the_list_indent`. A second, smaller find
from the same reading: blank lines inside the block were being indented, leaving
invisible trailing whitespace.

**4. I broke `StageBindings` and the suite caught it.** Inserting `DocEntry`
above it by string match landed the new class *between* `@dataclass` and
`class StageBindings:`, leaving `StageBindings` undecorated and its fields as
`Field` objects. Three tests failed with `TypeError: 'Field' object is not
iterable`. Entirely self-inflicted, caught immediately, and worth recording
because a scripted edit that matches on a bare `class` line will do this again.

**5. The plan's Documentation Sync table under-read its own entry.** The entry
path is `skills/<component>/SKILL.md`, a **pattern**. Two files still presented
the Markdown form as primary and were missed by the first pass: the
`/tcw-docs-sync-setup` command description, and the README's skill list. Both
fixed. This is the second item in a row where reading that entry as one file
rather than a pattern cost a correction.

## Notes

- **This repository's own entry is a path that resolves to nothing.**
  `skills/<component>/SKILL.md` is a pattern, so requiring entry paths to exist
  would have rejected the node writing the rule. The spec called this out and a
  test now pins it (`test_a_path_placeholder_survives_this_repos_own_config`).
- **The verb's stdout is empty on an unconfigured node**, with the explanation on
  stderr. A caller piping `tcw work docs` gets no rows rather than a sentence
  pretending to be one; `--json` is the branch a program should use.
- **`tcw work docs` was worth building even though two of three invocation points
  are stages.** The third — the version offer after `complete` — has no stage,
  because `tcw work stage implement` on a completed item is refused by the status
  check. Without the verb that path would still be scraping Markdown.
- **The `## Versioning` section is untouched**, and remains the same class of
  defect. It is the sibling item, now specced and reviewed.
- Reviewed by `codex` at `spec`. `bllm-review` was not attempted; it produced
  nothing on the first item of this session after 1440s on a workload lock, and
  the bug is filed to `/Users/brian/llama/docs/work/inbox/`.

---

# Rework outcome — the recommended form, said once

`rework.md` holds the analysis. Two things changed; one thing was checked and
found not to be a problem at all.

## The rework's own premise did not hold

I sent this back to resolve a "two sources of truth" collision between the
`work.documentation` config block and the `## Documentation Sync` heading the
skill name-matches. **There is no collision.** The skill asks `tcw work docs
--json` first and is told, for `source: "config"`, to "use it and read no
Markdown"; this node reports `source: config` with all four entries; and the
Markdown section that remains contains no entries to be confused by.

Third time in this release that I argued from a failure I had not executed.
Recorded in `rework.md` and carried to the post-mortem.

## What did change

**`skills/documentation-sync/SKILL.md`.** The heading `## The Documentation Sync
Section` opened with "Project owners add this section to their `CLAUDE.md`" — read
cold, a recommendation for the legacy form, contradicting both the top of the same
file and `references/setup.md`. Retitled to name itself the fallback and led with
the config form and a pointer to `setup.md`. The bullet-list example stays; it is
the fallback's format reference and is still needed outside a TCW node.

This is a real gap in the acceptance criteria, not just wording. Criterion 11a
required that no file instruct a reader to **find** entries in Markdown except as
the fallback. It was met. Nothing covered instructing a reader to **create** them
there.

**`tests/test_documentation_sync_wiring.py`** gains two tests, written red first:
one asserts the section names itself the fallback and points at the config form,
the other that `SKILL.md` and `setup.md` do not contradict each other. Without a
test the framing drifts straight back — it already had.

**`spec.md` criterion 11 amended.** It required the section be gone entirely;
implementation kept it minus the entries and filed a deviation arguing the
directive line has nowhere else to live. The argument is right, so the criterion
is corrected. A criterion the work knowingly does not meet, with the reasoning
parked in `outcome.md`, reads at a glance like a gap.

## Scope held

No production code. Nothing under `tcw/` changed, and the Markdown fallback stays
— it is the only option outside a TCW node, and this skill ships to projects that
are not TCW nodes.
