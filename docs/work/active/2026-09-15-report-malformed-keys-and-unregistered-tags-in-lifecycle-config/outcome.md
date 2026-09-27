# Outcome: report malformed keys and unregistered tags in lifecycle config

## What shipped

- **Code** — `c85666af`: the six join sites in `tcw/store/base.py` sort
  `map(str, keys)`; `_parse_condition` refuses commas and unnormalizable
  elements and normalizes the rest; `_parse_binding` checks a `skill:` value's
  shape; in `tcw/store/fs.py`, `_condition_tag_problems` (via
  `lifecycle_problems`), `_registered_tag_entries` behind `registered_tags`,
  normalized plan-stage tags, `_validate_tags` refusing a non-string; in
  `tcw/work/cli.py`, the `list --tags` note. Tests:
  `tests/test_lifecycle_config_tags.py`; `tests/test_lifecycle_hooks.py`'s
  skill-never-executed test given a value that passes the new shape check.
- **Docs** — `2fbde1cc`, `8e2541e7`: changelog, release notes,
  `docs/guide/configuration.md`, `skills/configure/references/work.md`,
  `skills/work/references/hooks.md`.
- **Review fold-in** — condition-tag problems carry the binding index; plan-stage
  tags refuse commas; tests for transitions, artifacts and procedures; the
  behavior change worded exactly; the release note says a malformed `skill:`
  binding is ignored.

## Tests

- 23 of the new tests failed on the old code, each for its intended reason
  (confirmed independently by the reviewer on an extracted copy).
- `tests/test_lifecycle_config_tags.py`: 30 passed; related lifecycle, hooks,
  procedure, documentation and tag files: 196 passed.
- This repository's own `tcw validate` with the new rules: OK (it gates
  `complete` here).
- Full suite on the final code: see `refined-outcome.md`.
- Hands-on: a scratch node with `when: {tags: [CLI]}`, `[clii]`, `skill: "my
  skill"` and a `1:` key. Installed build: a `TypeError` traceback. Worktree
  build: three named problems; the `CLI` binding fired for a `cli` item; `tcw
  work list --tags nope` printed the note and exited 0.

## What the plan or spec got wrong

- "A binding that fires today keeps firing" overclaimed: a first-match artifact
  list can now be shadowed by a newly matching earlier condition, and a
  hand-edited `CLI` item tag stops matching a `CLI` condition. Spec and
  changelog corrected.
- The spec said a bad `skill:` value is *reported*; being a parse problem it is
  also dropped at runtime, like any malformed binding. Release note corrected.
- Tests went into one new file rather than the two existing ones the plan named.
- The web API's string `tags` case was already fixed before this item; what
  remained was a non-string element (`AttributeError`).

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | No | — |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Yes | `configuration.md`: condition tags and skill names. |
| `docs/release-notes/upcoming.md` | Yes | Four lines. |
| `docs/changelogs/upcoming.md` | Yes | Five Fixed entries, with the behavior change. |
| `skills/<component>/SKILL.md` | Yes | `skills/work/references/hooks.md`. |
| `skills/configure/references/` | Yes | `work.md`: what `tcw validate` now reports. |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Normalize or validate condition tags; how loud is an unregistered one?**
  Codex and Opus: normalize at parse, reject commas first, and report an
  unregistered condition tag as a real `tcw validate` problem outside the
  parser (validate already fails for an item's unregistered tag). Chose that.
- **`list --tags` typo: exit 0 with a note, or exit 1?** Both: exit 0 with a
  note (list reads; items may keep an unregistered tag), checking every listed
  node's registry under `-i`. Chose that.
- **`skill:` bindings.** Opus: shape check plus documentation. Codex: shape check
  plus naming the declaring config in the resolved text. Chose the shape check
  and documentation only: changing the resolved text alters instructions every
  agent reads and the prompt fixtures pin, and would still not catch a
  plausible typo.
- **Code review** (adversarial-code-reviewer): DONE, merge with notes. Accepted
  all five "belongs to this change" notes. Filed the two "separate change" notes
  as `2026-09-26-read-item-tags-normalized-and-keep-non-tag-work-tags-entries-visible`.
