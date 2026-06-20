# Skill layer + capabilities process (work Spec 3) — spec

**Status:** spec ✓ · build ☐
**Delivers:** the **judgment layer** that drives the `tcw` tools — two Claude Code skills (`tcw-work`, `tcw-capabilities`) — plus the one tool affordance the lifecycle handshake needs (`tcw capabilities set`).
**Depends on:** work Spec 1 (single-node core) and Spec 2 (cross-node recursion: `delegate`/`escalate`/`reconcile`/`--worktree`/`--initiative`) — both shipped. Capabilities component (Phase 3) — shipped.
**Source of truth:** this doc, derived from [`phase-6-beyond`](../../../plan/phase-6-beyond.md) (Spec 3), [`phase-5-work`](../../../plan/phase-5-work.md) Part C #3 + A.7, and [`phase-3-capabilities`](../../../plan/phase-3-capabilities.md) A.9 + Part C #3. Framework rules: [`../../../../AGENTS.md`](../../../../AGENTS.md).

> **Mechanism vs. judgment (the prime directive, applied).** Spec 2 added the cross-node *mechanisms*; Spec 3 adds the *judgment* that drives them — authored as **skills**, not tool code. The one exception is a structural *mechanism* the capabilities handshake genuinely lacks today (flipping a capability's status), which becomes a small, validated tool command. Everything else is markdown.

---

## 1. Scope

**In (this spec):**

- `skills/tcw-work/SKILL.md` — the continuous work-driving flow: recursive process-inbox, three-axis/product-first planning, the start/complete lifecycle handshake, resume, decompose (epics + child-node tasks).
- `skills/tcw-capabilities/SKILL.md` — the capabilities *process*: the `## Capability changes` planning gate, contradiction-detection, the ledger flip at completion, the product-layer coordination protocol.
- `tcw capabilities set <id> [--status S] [--field "K=V" …] [--commit]` — the ledger-flip mechanism (a `set` op on `CapabilitiesStore` + `FsCapabilitiesStore`).
- Tests for `set`; structure-check + a worked dry-run for the skills.

**Out (Spec 4, downstream — consumer repos):** retiring `skill-cefailures`'s `process-inbox`/`process-inbox-initiative` commands and the standalone `capabilities-sdlc` skill; redirecting Proposit doc-sync; reconciling consumer `AGENTS.md`/`ORCHESTRATOR-AGENTS.md`. Tracked in those repos.

**Out (other items):** packaging these skills as a distributable plugin (the "distribute tcw as a plugin" backlog item — command wrappers, marketplace manifest); tracker sync; the hard DoD gate.

---

## 2. Architecture stance (the litmus test)

The judgment lives in skills; the tool stays a mechanism. The one tool addition passes the litmus test — *"could a non-filesystem store flip a capability's status?"* Yes: it is a field write on a store node (the same shape as `WorkStore.set_field`). So `set` belongs on the `CapabilitiesStore` interface, realized by the FS adapter as an in-place markdown edit. Deciding *when* to flip (the handshake, contradiction-detection) stays in the skill.

| Concern | Where it lives | Why |
|---|---|---|
| when to triage / plan / decompose / escalate / flip a status | skills (`tcw-work`, `tcw-capabilities`) | judgment |
| flipping a capability's status/field | `CapabilitiesStore.set` + `FsCapabilitiesStore` | mechanism (a node field write) |
| inbox triage, resume, decompose orchestration | skills, over existing CLI commands | judgment over Spec 1/2 mechanisms |
| product-layer wording relay | `tcw-capabilities` skill over Spec 2's inbox channel | judgment riding an existing mechanism |

No new mechanism is added that only the FS adapter could honor.

---

## 3. The tool affordance — `tcw capabilities set`

The lifecycle handshake's core act is flipping a capability's status (`Missing → Supported`, `Supported → Omitted`) and recording fields (e.g. `Planning doc:` at planning). Today `tcw capabilities` has `list/show/add/search/check` but **no way to change a field** — an agent would hand-edit markdown, error-prone for a structural transition. `set` fills exactly that gap.

### 3.1 Interface

- `CapabilitiesStore.set(identifier: str, fields: dict[str, str]) -> Capability` (abstract) — set/update the named metadata fields on the capability resolved by `identifier` (A.6 grammar, incl. `#heading`). Returns the updated capability.
- `FsCapabilitiesStore.set` realizes it as an **in-place edit of the inline metadata block**: for each `K=V`, update the existing `**K:** …` line, or insert a new `**K:** V` line at the end of the block (immediately before the blank line that precedes the body), preserving heading, body, sibling capabilities, and file formatting. Stages the file (`--commit` opts into a `tcw capabilities: …` commit, matching the other components).

### 3.2 Validation (reuses the locked vocabulary)

- `--status` value must be in `CAP_STATUSES`; refuse otherwise.
- Field keys must be in `CAP_FIELDS` (the locked set); refuse unknown fields.
- The identifier must resolve to exactly one capability (`#heading` required when the file holds more than one); error on dangling/ambiguous/collision (reuse `_resolve_file` / the `_IDENT_RE` + heading match already in the adapter).
- `set` does **not** enforce status *business-semantics* (e.g. it won't require `Gaps` when setting `Partial`) — that stays `check`'s job and the skill's judgment (A.12 mechanism-vs-judgment). It only writes valid fields.

### 3.3 CLI

```
tcw capabilities set <id> [--status S] [--field "K=V"]... [--commit]
```

`--status S` is sugar for `--field "Status=S"`. At least one of `--status`/`--field` is required.

---

## 4. The skills

Authored in Claude Code `SKILL.md` format (YAML frontmatter: `name`, `description` with explicit "Use when…" triggers), under `skills/` at the repo root. Both are **flexible** skills (judgment guides, not rigid checklists). They reference the `tcw` CLI by command, never reimplement tool logic, and cross-reference each other at the seams.

### 4.1 `skills/tcw-work/SKILL.md` — drive work items end-to-end

Trigger: starting/continuing/triaging/decomposing `tcw work` items; processing a `docs/work/inbox/`. Sections:

- **Recursive process-inbox.** Enumerate `docs/work/inbox/` (this node) — both raw request docs (incl. `delegate`/`escalate` drops carrying `from:`/`initiative:` front-matter) and any inbox-status item folders. For a raw doc: read it → `tcw work new "<title>" [--initiative <slug>]` piping the body → `git rm` the doc (it has been ingested into a tracked item). Across child nodes (`tcw work nodes`), an orchestrator triages its own inbox and *delegates* down rather than reaching into a child's tree.
- **Three-axis / product-first planning.** Fill `## Product / Technical / Meta changes`. **Product-first:** if there is any product delta, invoke the `tcw-capabilities` skill's planning gate (§4.2) *before* writing the technical plan. Which sections are non-empty is the classification.
- **The lifecycle handshake.** `new` (declare delta; record `Missing` capabilities — §4.2) → `tcw work start` (optionally `--worktree` for isolation) → during `active`, contradiction-detection on any capability change (§4.2) → `tcw work complete --resolution … --confirm`, whose DoD "capabilities reconciled" item is satisfied by the §4.2 ledger flip.
- **Resume.** Re-enter across sessions: `tcw work list --status active` → `tcw work show <slug>` → read the item's `content.md`/`spec.md`/`plan.md`; for an epic, `tcw work reconcile <slug>` to refresh the rollup before deciding the next action.
- **Decompose.** Turn a large item into an epic (`tcw work new --epic`) + child-node tasks (`tcw work delegate <child> …` then the child runs process-inbox and `tcw work new --initiative <epic>`); track via `tcw work reconcile`.

### 4.2 `skills/tcw-capabilities/SKILL.md` — the capabilities process

Trigger: planning/completing a work item with a product delta; coordinating capability wording across nodes. Sections:

- **`## Capability changes` planning gate.** When a work item has a product delta, name each new/changed/removed capability and record it in `docs/capabilities/`: `tcw capabilities add <id> --status Missing`, then `tcw capabilities set <id> --field "Planning doc=<work-slug>"` (the capability→work forward pointer). Existing capabilities being changed are noted in the item's `capabilities.yaml` (the work→capability back-pointer).
- **Contradiction-detection (at the moment of change).** Before recording/altering a capability, check it against the standing ledger: `tcw capabilities search`/`show` for an existing capability that the change would contradict (e.g. a new capability that conflicts with a `Supported` one, or a status that disagrees with reality). Run `tcw capabilities check`. Surface contradictions to the human rather than silently overwriting.
- **The ledger flip at completion.** As the work item's final pre-freeze step (the DoD "capabilities reconciled"): apply each declared delta — `tcw capabilities set <id> --status Supported` (Missing→Supported), scope/body edits, `--status Omitted` (Supported→Omitted) — so the standing ledger describes the present.
- **Product-layer coordination protocol (orchestrator-relay).** A per-node agent does **not** read the orchestrator's `docs/capabilities/`. To get canonical product-layer wording it **escalates a request** over the inbox channel (`tcw work escalate "capability wording: <name>"`); the orchestrator replies (delegates back) with canonical wording, then flips the **product-layer** entry when the **epic** completes. When coordination is unavailable, the node falls back to in-repo evidence and marks the entry `TODO: confirm wording`. Recursion: an **epic** completing flips the product-layer entry; a **task** completing flips the leaf entry (phase-3 A.9).

### 4.3 Skill authoring constraints

- Use `superpowers:writing-skills` to author and self-check both skills.
- Each skill is one `SKILL.md` (split to sub-docs only if a section is large and conditionally needed — `writing-skills`' progressive-disclosure rule).
- Skills name `tcw …` commands and the *other* tcw skill by name; they never duplicate the locked vocabulary or the store internals (single source of truth stays the component specs + the tool).

---

## 5. Testing

- **`tcw capabilities set` (pytest, `tests/test_capabilities.py`):** set an existing field's value (`Status` Missing→Supported); insert a not-yet-present field (`Planning doc`) preserving the body and sibling capabilities; resolve a `#heading` id in a multi-capability file; refuse an invalid status; refuse an unknown field key; error on a dangling/ambiguous id; stage-only by default, `--commit` commits. CLI: `--status` sugar maps to `Status=`; requires at least one of `--status`/`--field`.
- **Skills:** no pytest (markdown). Verify via (a) `writing-skills`' structure self-check — valid frontmatter, an explicit "Use when…" trigger, no broken cross-references; and (b) a **worked dry-run** captured in the plan: in a throwaway node, run inbox-doc → `tcw work new` → planning gate (`capabilities add`/`set`) → `tcw work start` → `tcw capabilities set --status Supported` → `tcw work complete`, confirming each command the skill calls exists and behaves as the skill claims.

---

## 6. Documentation sync (per CLAUDE.md)

- **`README.md`** [Public-API] — document `tcw capabilities set`; add a short "Skills" section pointing at `skills/tcw-work` and `skills/tcw-capabilities` (what drives the tools).
- **`docs/release-notes/upcoming.md`** [Public-API] — plain language: a command to update a capability's status/fields, and the two skills that drive the work + capability lifecycle.
- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — Added: `CapabilitiesStore.set` + `FsCapabilitiesStore` + `tcw capabilities set`; the two skills. With commit-hash range.
- **`docs/plan/phase-6-beyond.md`** — mark "Skill layer + capabilities process (work Spec 3)" built.
- **`docs/plan/phase-3-capabilities.md`** — B.2 gains `set`; note A.9's product-layer coordination is now realized as the `tcw-capabilities` skill.
- **`docs/plan/phase-5-work.md`** — Part C #3 built.

---

## 7. Build checklist

1. `CapabilitiesStore.set` (abstract) + `FsCapabilitiesStore.set` (in-place inline-field edit, validation) + `tcw capabilities set` CLI + tests (§5).
2. `skills/tcw-work/SKILL.md` (via `writing-skills`).
3. `skills/tcw-capabilities/SKILL.md` (via `writing-skills`).
4. Worked dry-run of the skills against the real CLI (§5); fix any command/skill mismatch.
5. Documentation sync (§6).
