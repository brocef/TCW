# Refined outcome — Serve documentation-sync entries from `tcw-config.yaml`

**Accepted.** The user approved closeout on 2026-08-19, after one rework.

## The decision

Accepted. This is the item that makes the documentation gate configuration rather
than prose an agent has to find and parse.

## Evidence

- **`tcw work docs [--json]`** returns `{"schema": 1, "source":
  "config"|"agent-guide", "entries": [...]}`. On this node: `source: config`
  with all four entries, in configured order.
- **`tcw work stage plan` and `implement`** print the entries inline on a
  configured node and name the agent guide on an unconfigured one. 31 tests in
  `tests/test_documentation_prompt.py`, 33 in `tests/test_documentation_config.py`.
- **Back-compat is evidence, not assertion.** `tests/fixtures/prompt_fallback/`
  was captured **before any prompt was touched**, in its own commit (`8575993`),
  and `tests/test_prompt_fallback.py` (8 tests) replays it. An unconfigured node's
  output is byte-identical to the pre-1.0.0 output.
- **`tcw work docs` writes nothing** — pinned by hashing every path in the node
  before and after, not by `git status`, which a write-then-restore would pass.
- Full suite green at closeout.

## The rework, and a premise that did not hold

I sent this back at `verify` to resolve a "two sources of truth" collision
between the `work.documentation` config block and the `## Documentation Sync`
heading the skill name-matches as its fallback. **Checked: there is no
collision.** The skill asks `tcw work docs --json` first and, for
`source: "config"`, is told to "use it and read no Markdown"; this node reports
`source: config`; and the section that remains holds no entries at all.

The rework found a **real but smaller** defect while looking. `SKILL.md`'s
`## The Documentation Sync Section` opened with "Project owners add this section
to their `CLAUDE.md`" — read cold, a recommendation for the legacy form,
contradicting both the top of the same file and `references/setup.md`. Criterion
11a required that no file instruct a reader to **find** entries in Markdown
except as the fallback; nothing covered instructing them to **create** entries
there. Retitled, reframed, and pinned by two tests written red first.

**Criterion 11 was amended rather than deviated from.** It required the section
be gone entirely; implementation kept it minus the entry list and filed a
deviation arguing the skill's own `setup.md` says to "always include the opening
directive line", which is not an entry and has nowhere else to live. That
argument is right, so the criterion was corrected — a criterion the work
knowingly does not meet, with the reasoning parked in `outcome.md`, reads at a
glance like a gap.

## Design deviations from the spec, both deliberate

- **The span carries its own fallback.** The spec assumed one token with the
  fallback string held in Python. The two prompts word the instruction
  differently, so one constant could not reproduce both byte-for-byte. Putting
  the fallback inside the span makes back-compat hold *by construction*.
- **Rendering is a list, not a table.** A `|` in a description would break a
  table silently. Continuation lines indent to the token's column, and prose
  after a span resumes at the list indent rather than one column deeper — at four
  spaces after a list, CommonMark reads it as a code block. That was a
  correctness bug, not a cosmetic one, and it has a test.

## Capability ledger

Reconciled: `tcw capabilities drift` reports **no capability drift**.

## Closeout choices

- **Merge route:** none needed — all work landed directly on `main`.
- **Documentation:** `README.md`, both `upcoming.md` files, the migration guide,
  and `skills/documentation-sync/` all updated during implementation and rework.
- **Version:** folded into the unpushed **v1.0.0**. Gate re-run immediately
  before: `STATUS: FOLDABLE`, exit 0.
- **Follow-up:** none filed for this item.

## Notes

Validation is **shape-only** by design and should stay that way: the trigger
vocabulary is explicitly open, and `path` is not required to exist — this
repository's own fourth entry is the pattern `skills/<component>/SKILL.md`.
