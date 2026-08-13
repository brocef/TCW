# Cross-Node Capability Declarations Implementation Plan

_Compressed, at the user's direction. No runtime change, so the usual task-per-module structure would be ceremony; the work is five capability folders and one verification pass._

**Goal:** Five accurate `Supported` capabilities covering `nodes`, epics, `reconcile`, `delegate`, and `escalate`.

**Architecture:** `tcw capabilities add` / `set` for structure and fields; `description.md` written by hand. No `tcw/` file is touched.

## Global Constraints

- Every claim in a body comes from source or live CLI output — never from `README.md` or `--help`. The `delegate --help` finding in `spec.md` is the standing proof that those disagree with the code.
- Never hand-edit `meta.yaml` where `tcw capabilities set` applies.
- Do not modify any existing capability.
- Do not fix the `delegate --help` string here; it is a runtime change and needs its own item.

---

### Task 1: Declare the five capabilities

**Files:** `docs/capabilities/work/{inspect-the-node-topology,coordinate-a-cross-node-epic,reconcile-an-epic-rollup,delegate-a-request-to-a-child-node,escalate-a-request-to-the-parent-node}/`

- [ ] **Step 1: Create structure and fields**

For each of the five, per the `spec.md` table:

```bash
tcw capabilities add <path> "<Name>" --status Supported
tcw capabilities set <path> --field "Subject=<terms>" --field "Feature=<feature>"
```

- [ ] **Step 2: Re-read the source for each before writing its body**

Not optional, and the ordering matters — read, then write:

| Capability | Read |
| --- | --- |
| inspect-the-node-topology | `_nodes` in `tcw/work/cli.py`; `child_nodes` / `parent_node` in `tcw/store/fs.py` |
| coordinate-a-cross-node-epic | the initiative gates in `tcw/work/cli.py` and `epic_completable` in `tcw/store/fs.py` |
| reconcile-an-epic-rollup | `reconcile` and `_render` in `tcw/work/recursion.py` |
| delegate-… / escalate-… | `delegate`, `escalate`, `_inbox_write` in `tcw/work/recursion.py` |

- [ ] **Step 3: Write each `description.md`** with the content `spec.md` § Design requires. Use `tcw://C/<path>` prose links between the epic and rollup entries.

- [ ] **Step 4: Verify structure before content review**

```bash
tcw capabilities check
tcw capabilities list | grep -c .            # expect 65
tcw capabilities list | grep -cE '	work/'   # expect 28
git status --short                            # expect only new files under docs/capabilities/work/
```

Covers criteria 1-3 and 5.

- [ ] **Step 5: Commit**

```bash
git add docs/capabilities/work
git commit -m "docs: declare the cross-node recursion capabilities"
```

---

### Task 2: Verification and evidence

- [ ] **Step 1: Full gate**

```bash
python -m pytest -q
tcw taxonomy check && tcw capabilities check && tcw capabilities drift && tcw validate
git diff --check && git status --short
git diff --stat HEAD~1 -- tcw   # expect empty (criterion 6)
```

Covers criteria 6-8.

- [ ] **Step 2: Documentation Sync** — evaluated up front rather than deferred, since the answer is short. `README.md`: does **not** fire; it already documents all five commands and this item adds no behavior. `docs/release-notes/upcoming.md`: does **not** fire; nothing changes for a user of the tool. `docs/changelogs/upcoming.md`: **fires** (`Any-Code-Change` covers the ledger content shipped in the package) — one `Added` line naming the five paths. `skills/<component>/SKILL.md`: does **not** fire; no CLI surface, model, lifecycle, or guardrail change. Record all four decisions in `outcome.md` so the skips read as evaluated.

- [ ] **Step 3: Write and commit `outcome.md`**, then stop. Record the `--help` finding as a follow-up needing its own item. Do not submit, complete, or cut a version without the later lifecycle gates and explicit user authorization.

## Verification Beyond the Suite

- **No test can tell whether these descriptions are true.** `tcw capabilities check` validates structure and that `Feature` resolves; it cannot know whether the prose matches the code. Re-read each body against the source it describes as a final pass — that reading *is* this item's real verification.
- Confirm no new entry duplicates `work/view-the-board`'s account of `--include-descendants`.
