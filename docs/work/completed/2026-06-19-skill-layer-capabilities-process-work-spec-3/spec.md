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
- `tcw capabilities set <id> [--status S] [--field "K=V" …]` — the ledger-flip mechanism (a `set` op on `CapabilitiesStore` + `FsCapabilitiesStore`; stage-only).
- Tests for `set`; structure-check + a worked dry-run for the skills.

**Out (Spec 4, downstream — consumer repos):** retiring `skill-cefailures`'s `process-inbox`/`process-inbox-initiative` commands and the standalone `capabilities-sdlc` skill; redirecting Proposit doc-sync; reconciling consumer `AGENTS.md`/`ORCHESTRATOR-AGENTS.md`. Tracked in those repos.

**Out (other items):** packaging these skills as a distributable plugin (the "distribute tcw as a plugin" backlog item — command wrappers, marketplace manifest); tracker sync; the hard DoD gate.

---

## 2. Architecture stance (the litmus test)

The judgment lives in skills; the tool stays a mechanism. The one tool addition passes the litmus test — *"could a non-filesystem store flip a capability's status?"* Yes: it is a field write on a store node (abstractly like `WorkStore.set_field`, though capability fields live **inline in markdown**, not in a separate YAML state file — so the FS realization is an in-place markdown edit, not a YAML write). So `set` belongs on the `CapabilitiesStore` interface; deciding *when* to flip (the handshake, contradiction-detection) stays in the skill.

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

`FsCapabilitiesStore.set` realizes it as an **in-place, line-based edit scoped to one `## <name>` block** — the parser (`parse_capability_file`) discards line positions and there is no markdown serializer, so `set` must locate and edit the block itself rather than round-trip through the parser. The algorithm:

1. **Resolve the file** via `_resolve_file` (flat / folder-entry `capabilities.md` / `[state]` variant — **never a sidecar**, which `_resolve_file` does not reach by bare path). Read its lines.
2. **Locate the capability block.** Split on `^## ` boundaries (as the parser does). If the file holds more than one capability, a `#heading` is **required**; match the block whose `heading_slug(name)` equals it, else error (ambiguous). The block spans from its `## ` line to the next `^## ` or EOF.
3. **Find the metadata run** — within the block, the maximal run of consecutive lines (after `.strip()`) matching `_FIELD_RE`, starting on the line immediately after the heading. (After `add`, this run always has at least `**Status:**`.)
4. **Update or insert.** For each `K=V`: if a `**K:** …` line exists in the run, rewrite it in place; otherwise insert a new `**K:** V` line at the **end of the run** (immediately after the last field line; or immediately after the heading if the run is empty). **Never key off a blank line.** Insertion at the end of the run keeps the new field inside the block and out of the body.
5. **Write back** the modified lines, preserving the heading, body, sibling `##` blocks, and surrounding files. **Stage** the file (stage-only, matching `add` and `taxonomy add` — no `--commit`).

`set` performs **no file creation or folder promotion**, so the flat-file-vs-folder collision rule (A.3) is unaffected, and it operates only on capability files (flat / `capabilities.md` / `[state]` variant) — the same reach as `get`, never sidecars.

### 3.2 Validation (reuses the locked vocabulary)

- `--status` value must be in `CAP_STATUSES`; refuse otherwise.
- Field **keys** must be in `CAP_FIELDS` (the locked set); refuse unknown keys.
- The identifier must resolve to exactly one capability: **`#heading` is required when the resolved file holds more than one** (`set` parses + counts and errors otherwise); error on dangling/ambiguous/collision (reuse `_resolve_file` + the heading match in `_ref_error`).
- `set` validates the **`Status` value** (the primary affordance) and field **keys** only. Other field **values** (`Priority`/`Lifecycle` enums, `Roles`/`When`/`Subject`/`Superseded by` ref resolution) and status *business-semantics* (e.g. requiring `Gaps` on `Partial`) are **not** checked by `set` — that stays `check`'s job and the skill's judgment (A.12). It writes a syntactically valid field; `tcw capabilities check` is the semantic gate.

### 3.3 CLI

```
tcw capabilities set <id> [--status S] [--field "K=V"]...
```

`--status S` is sugar for `--field "Status=S"`. At least one of `--status`/`--field` is required (an explicit argparse-level check). `--field` is repeatable (`action="append"`). Stage-only, like every other capabilities/taxonomy write.

---

## 4. The skills

Authored in Claude Code `SKILL.md` format (YAML frontmatter: `name`, `description` with explicit "Use when…" triggers), under `skills/` at the repo root. Both are **flexible** skills (judgment guides, not rigid checklists). They reference the `tcw` CLI by command, never reimplement tool logic, and cross-reference each other at the seams.

### 4.1 `skills/tcw-work/SKILL.md` — drive work items end-to-end

Trigger: starting/continuing/triaging/decomposing `tcw work` items; processing a `docs/work/inbox/`. Sections:

- **Recursive process-inbox.** Enumerate `docs/work/inbox/` (this node) — raw request docs, including `delegate`/`escalate` drops carrying `---\nfrom: …\n[initiative: …]\n---` front-matter. (Inbox holds raw `.md` docs only; `tcw work new` creates a **backlog** item folder, never an inbox folder — there is no "inbox item folder.") For each doc: read it, **extract `initiative:`/`from:` from the front-matter**, then `tcw work new "<title>" [--initiative <slug>]` piping the **body with the front-matter stripped** (`tcw work new` reads the body from stdin but does not parse front-matter, so the skill strips it) → the item lands in `backlog/` → `git rm` the source doc (it has been ingested). `tcw work start` later promotes it to active. Across child nodes (`tcw work nodes`), an orchestrator triages its own inbox and *delegates* down rather than reaching into a child's tree.
- **Three-axis / product-first planning.** Fill `## Product / Technical / Meta changes`. **Product-first:** if there is any product delta, invoke the `tcw-capabilities` skill's planning gate (§4.2) *before* writing the technical plan. Which sections are non-empty is the classification.
- **The lifecycle handshake.** `new` (declare delta; record `Missing` capabilities — §4.2) → `tcw work start` (optionally `--worktree` for isolation) → during `active`, contradiction-detection on any capability change (§4.2) → `tcw work complete --resolution … --confirm`, whose DoD "capabilities reconciled" item is satisfied by the §4.2 ledger flip.
- **Resume.** Re-enter across sessions: `tcw work list --status active` → `tcw work show <slug>` → read the item's `content.md`/`spec.md`/`plan.md`; for an epic, `tcw work reconcile <slug>` to refresh the rollup before deciding the next action.
- **Decompose.** Turn a large item into an epic (`tcw work new --epic`) + child-node tasks (`tcw work delegate <child> …` then the child runs process-inbox and `tcw work new --initiative <epic>`); track via `tcw work reconcile`.

### 4.2 `skills/tcw-capabilities/SKILL.md` — the capabilities process

Trigger: planning/completing a work item with a product delta; coordinating capability wording across nodes. Sections:

- **`## Capability changes` planning gate.** When a work item has a product delta, name each new/changed/removed capability and record it in `docs/capabilities/`. For a *new* capability: `tcw capabilities add <namespace/path> "<Capability name>" --status Missing` (which seeds `**Status:** Missing`; the heading slug derives from the name), then `tcw capabilities set <namespace/path> --field "Planning doc=<work-slug>"` (the capability→work forward pointer; a freshly-`add`ed file is single-capability, so the bare id resolves). Existing capabilities being changed are recorded in the item's `capabilities.yaml` (the work→capability back-pointer, defined in phase-5-work B.4).
- **Contradiction-detection (at the moment of change).** Before recording/altering a capability, check it against the standing ledger: `tcw capabilities search`/`show` for an existing capability that the change would contradict (e.g. a new capability that conflicts with a `Supported` one, or a status that disagrees with reality). Run `tcw capabilities check` (exit non-zero ⇒ structural problems to resolve first). Whether two capabilities semantically *contradict* is judgment — surface candidates to the human rather than silently overwriting.
- **The ledger flip at completion.** As the work item's final pre-freeze step: apply each declared delta — `tcw capabilities set <id> --status Supported` (Missing→Supported), scope/body edits, `--status Omitted` (Supported→Omitted) — so the standing ledger describes the present. At completion these are long-lived multi-capability files, so the `id` carries a `#heading` (§3.2). The flip satisfies the DoD "capabilities reconciled" item by *convention* — that DoD item is acknowledged (printed at `complete`), **not** verified by the tool (phase-5 B.6 loose gate; the hard gate is a deferred hook). Flips are best-effort and idempotent (re-running `set` to the same status is a no-op), not a transaction — consistent with the pointer-not-transaction model (phase-3 A.8).
- **Product-layer coordination protocol (orchestrator-relay).** A per-node agent does **not** read the orchestrator's `docs/capabilities/`. To get canonical product-layer wording it **escalates a request** over the inbox channel (`tcw work escalate "capability wording: <name>"`); the orchestrator replies (delegates back) with canonical wording, then flips the **product-layer** entry when the **epic** completes. The protocol is **non-blocking**: a node never waits on a reply — if canonical wording isn't available when it's needed, the node falls back to in-repo evidence and marks the entry `TODO: confirm wording` (the fallback *is* the timeout behavior). Recursion: an **epic** completing flips the product-layer entry; a **task** completing flips the leaf entry (phase-3 A.9).

### 4.3 Skill authoring constraints

- Use `superpowers:writing-skills` to author and self-check both skills.
- Each skill is one `SKILL.md` (split to sub-docs only if a section is large and conditionally needed — `writing-skills`' progressive-disclosure rule).
- Skills name `tcw …` commands and the *other* tcw skill by name; they never duplicate the locked vocabulary or the store internals (single source of truth stays the component specs + the tool).

---

## 5. Testing

- **`tcw capabilities set` (pytest, `tests/test_capabilities.py`):**
  - update an existing field's value (`Status` Missing→Supported) — assert the parsed `Status` changed and the body + sibling `##` blocks are byte-identical except that line;
  - insert a not-yet-present field (`Planning doc`) — assert it lands inside the metadata run (parser re-reads it as a field, not body) and the body is preserved;
  - resolve a `#heading` id in a **multi-capability** file and edit only that block; assert a sibling block is untouched;
  - **error** when the id omits `#heading` for a multi-cap file; error on a dangling/ambiguous id;
  - refuse an invalid `Status` value; refuse an unknown field key;
  - stage-only (assert the file is staged, no commit created);
  - CLI: `--status` sugar maps to `Status=`; requires at least one of `--status`/`--field`; **`tcw capabilities set <id> …` is not rewritten to `show`** (the normalizer regression — proves `"set"` is in `SUBCOMMANDS`).
- **Skills:** no pytest (markdown). Verify via (a) `writing-skills`' structure self-check — valid frontmatter, an explicit "Use when…" trigger, no broken cross-references; and (b) a **worked dry-run** in a throwaway node, asserting concretely at each step: inbox doc (with front-matter) → `tcw work new` lands the item in **`backlog/`** → planning gate `tcw capabilities add <ns/path> "<Name>" --status Missing` + `set --field "Planning doc=…"` → `tcw work start` moves it to `active/` → `tcw capabilities set <id>#<heading> --status Supported` flips the parsed status → `tcw work complete --resolution done --confirm` moves it to `completed/`. The dry-run confirms every command + flag the skills call exists and behaves as claimed (and that the "capabilities reconciled" DoD item is acknowledged, not verified).

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

1. `CapabilitiesStore.set` (abstract) + `FsCapabilitiesStore.set` (in-place inline-field edit per §3.1, validation per §3.2). Then wire the CLI in `tcw/capabilities/cli.py`: **add `"set"` to `SUBCOMMANDS`** (else the top-level `show`-sugar normalizer rewrites `set` → `show set …` and it fails), register the `set` subparser (`id` positional, `--status`, repeatable `--field` via `action="append"`), and the `_set` handler (map `--status`→`Status=`, require ≥1 of `--status`/`--field`). Tests per §5 (incl. the normalizer regression).
2. `skills/tcw-work/SKILL.md` (via `writing-skills`).
3. `skills/tcw-capabilities/SKILL.md` (via `writing-skills`).
4. Worked dry-run of the skills against the real CLI (§5); fix any command/skill mismatch.
5. Documentation sync (§6).
