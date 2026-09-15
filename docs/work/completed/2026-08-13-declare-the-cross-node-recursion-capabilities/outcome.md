# Outcome — Declare the cross-node recursion capabilities

## What shipped

Five capabilities under `docs/capabilities/work/`, all `Supported`, created with
`tcw capabilities add` / `set` (no hand-edited `meta.yaml`), bodies written by
hand (`032adf6`):

| Path | id | Subject | Feature |
| --- | --- | --- | --- |
| `work/inspect-the-node-topology` | `cap-e34b50` | `node` | `connected-project-registry` |
| `work/coordinate-a-cross-node-epic` | `cap-1ba750` | `work-item`, `node` | `connected-project-registry` |
| `work/reconcile-an-epic-rollup` | `cap-afa3f6` | `work-item`, `node` | `connected-project-registry` |
| `work/delegate-a-request-to-a-child-node` | `cap-432c9b` | `node` | `work-inbox` |
| `work/escalate-a-request-to-the-parent-node` | `cap-45a1e7` | `node` | `work-inbox` |

Each body was written **after** re-reading the source it describes, per the plan's
Task 1 Step 2 — `_nodes` in `tcw/work/cli.py`, the initiative gates in
`tcw/work/cli.py` and `epic_completable`/`complete` in `tcw/store/base.py`,
`reconcile`/`_render` and `delegate`/`escalate`/`_inbox_write` in
`tcw/work/recursion.py`. Several details in the bodies exist only because of that
reading and are not in `README.md`: that a slice counts as closed when *resolved*
(discarded included, so abandoned work cannot pin an epic open), that an epic with
no slices is never ready to close, that the rollup degrades to a skipped row on one
slice's malformed sidecar rather than failing, and that duplicate request titles
get a numeric suffix.

Changelog entry added (`Any-Code-Change`); see the Documentation Sync record below.

## Documentation Sync

Evaluated against `CLAUDE.md`; recorded so the skips read as decisions, not
omissions.

| Entry | Trigger | Fired? |
| --- | --- | --- |
| `README.md` | `Public-API` | **No** — it already documents all five commands under "Cross-node recursion"; this item adds no behavior and changes no CLI surface. |
| `docs/release-notes/upcoming.md` | `Public-API` | **No** — nothing changes for a user of the tool. Announcing "we wrote documentation about features you already had" is noise. |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **Yes** — the ledger ships in the package. One `Added` entry. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **No** — no CLI surface, model/field, lifecycle, or guardrail change. |

## What the plan and spec got wrong

Nothing material. Both were written after the `--help` finding below was already
in hand, so the usual back-fill trap — describing documentation instead of code —
was closed before implementation started.

One refinement worth recording: the spec predicted the ledger would reach 65
capabilities and 28 under `work/`. Both were exact, which is weak evidence the
scope was understood rather than guessed.

## Finding: `tcw work delegate --help` is wrong

Not fixed here — it is a runtime change and this item's spec put runtime changes
out of scope — but it is the reason several claims in
`delegate-a-request-to-a-child-node` are written the way they are.

`--help` describes the first argument as `child node path (relative to this
node)`. It is the **canonical project ID**. `delegate` builds
`{registered_project_id(node_root, c): c for c in child_nodes(node_root)}` and
matches against that. Verified on a fixture where directory name and project ID
deliberately differ:

```
'sub-dir-name'   -> ValueError: no child node 'sub-dir-name'. children: canonical-id
'canonical-id'   -> OK  …/sub-dir-name/docs/work/inbox
```

The existing tests cannot catch it: `mk_node` derives the project ID from the
directory name, so the two always coincide. **This needs its own item** — a
one-string fix plus a fixture whose ID and directory name differ.

Until it lands, the ledger and `--help` disagree. That is deliberate and recorded
here: the capability states the true behavior.

## Verification

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **1255 passed** (was 1250; the ledger is parameterized over by existing tests) |
| `tcw capabilities check` | `capabilities OK` — validates that every `Feature` resolves to a taxonomy entry of kind Feature |
| `tcw capabilities list` | 65 total, 28 under `work/` — both as the spec predicted |
| `tcw taxonomy check` | `taxonomy OK` |
| `tcw capabilities drift` | `no capability drift` |
| `tcw validate` | `validate OK` — every `tcw://C/…` prose link in the five bodies resolves |
| `git diff --stat HEAD~1 -- tcw` | empty — no runtime file touched |
| `git status --short` | clean |

### Verification beyond the suite

The plan is explicit that no test can tell whether these descriptions are *true* —
`capabilities check` validates structure and reference resolution, not prose. The
real verification was reading each body back against its source, which is what
produced the `--help` finding. Overlap with `work/view-the-board` was checked
specifically: it owns `--include-descendants` board aggregation, and
`inspect-the-node-topology` links to it rather than restating it.

## Notes

- Planning was compressed at the user's direction, and granularity (five
  per-command entries rather than three merged) was their call too.
- The five bodies cross-link with `tcw://C/…` rather than repeating each other, so
  the epic, rollup, topology, and two request capabilities read as one area.
- Out of scope and still open: auditing the rest of the ledger for further gaps.
  This item covered only the area that was found.
