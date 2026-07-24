# Plan — Absorb the documentation-sync skill into TCW

Single-context change: one new skill (3 files), a handful of reference rewires, one guard test, and
doc-sync self-application. No staged plan documents — splitting would not reduce the context a later
agent must load. Phases are mostly sequential; the only hard ordering is **skill files before the
references that point at them**.

Spec open decisions — **confirmed by user**: skill folder `documentation-sync`; setup as
`references/setup.md` (no slash command); one-line lifecycle handoff.

## Phase 1 — Port the skill (`skills/documentation-sync/`)

Create the skill first (nothing may reference it until it exists).

1. `skills/documentation-sync/SKILL.md` — thin router. Port from
   `skill-cefailures/skills/documentation-sync/SKILL.md`, adapted:
   - Trigger reference table: keep the four base triggers (`Public-API`, `Public-{Name}-API`,
     `Any-Code-Change`, `Only-Breaking`), the partition rule, and the public-surface judgment call.
   - Add a **"projects may define additional named triggers"** paragraph, using TCW's
     `Skill-Driven-Component` (from `AGENTS.md:54`) as the worked example — this is what reconciles the
     skill with AGENTS.md.
   - Evaluation loop + plan-integration guidance (named-file tasks vs. one re-evaluation gate).
   - "When to offer version/changelog options": four options; bump path stays **generic** ("use the
     project's version-cut process — see its CLAUDE.md / Versioning section"); do **not** name
     `scripts/cut_version.py` here. Keep-current updates `upcoming.md` in place.
   - Companion-doc gates pointing at the two references below.
   - Common-mistakes table (trigger-evaluation slips only).
   - Strip every `skill-cefailures:*` command reference and the FOLLOWUPS row.
2. `skills/documentation-sync/references/release-notes-and-changelogs.md` — port from the source
   `docs/release-notes-and-changelogs.md`, adapted: version-cut/rotation steps defer generically to
   "the project's version-cut process" (no hardcoded path); keep RN-vs-changelog, entry + hash-range
   format, version cross-check, migration offers.
3. `skills/documentation-sync/references/setup.md` — port from the source `commands/.../setup.md`,
   adapted: scaffolds a `## Documentation Sync` section into a project's CLAUDE.md and creates missing
   tracked files/dirs; **drop FOLLOWUPS.md** — where the source offered a FOLLOWUPS log, recommend
   `tcw work new "<deferred item>"` instead.

Keep the skill **portable** — generic "the project's CLAUDE.md" framing, no TCW-only paths in the body.
Follow `AGENTS.md:45` thin-router rules; the two references are the on-demand splits.

## Phase 2 — Rewire in-repo references (after Phase 1)

4. `AGENTS.md:49` — change the directive to invoke TCW's own `documentation-sync` skill instead of
   `skill-cefailures:documentation-sync`.
5. `skills/tcw-work/references/task-lifecycle.md` — at the **plan** gate (§3, line ~60) and the
   **closeout** gate (line ~135), replace "evaluate Documentation Sync triggers" with an explicit
   "invoke the `documentation-sync` skill …" handoff. Optionally align the closeout decision list
   (line ~131) for uniformity.
6. `skills/tcw-work/references/epic-lifecycle.md` — same handoff at the plan gate (line ~49) and the
   completion gate (line ~98).

   **Handoff syntax:** plain prose that names the skill (e.g. "invoke the `documentation-sync` skill
   to evaluate triggers"), matching how these files already name `tcw-capabilities`. This is a Skill-
   tool invocation by name (`tcw:documentation-sync`), **not** a `tcw://` URI — `tcw://` is only for
   cross-object references in prose, not skill invocation.
7. `README.md:712-742` — add a sixth skill bullet for documentation-sync; change "five skills" →
   "six skills"; soften the closing CLI-driver framing so it no longer claims *all* skills drive the
   CLI (documentation-sync is a cross-cutting process skill). Target wording per spec §Rewiring.
8. `.codex-plugin/plugin.json:22` (`longDescription`) — "five skills" → "six", add documentation-sync
   to the enumeration, adjust the "driving the tcw CLI" tail.
9. `.claude-plugin/plugin.json:4` + `.claude-plugin/marketplace.json:10` — soften "skills that drive
   the tcw CLI" so the framing matches README/codex. These carry **no count** (nothing says "five"),
   so there's no count drift to fix — just the framing. Do it for consistency rather than leaving a
   split where two manifests still imply every skill drives the CLI.

**Leave untouched:** `docs/changelogs/v0.11.1.md` (frozen release) and the
`2026-07-22-evaluate-and-refine-the-plugin-skills…` backlog spec — both match a naive `grep "five
skills"` but are out of scope.

## Phase 3 — Regression guard test

10. Add a small pytest in a dedicated `tests/test_documentation_sync_wiring.py` (cleaner than appending
    to the version-lockstep manifest test — this guards wiring, not versions) asserting:
    - `skills/documentation-sync/SKILL.md`, `references/release-notes-and-changelogs.md`, and
      `references/setup.md` all exist (assert the reference files **by exact name**, so a filename-drift
      port is caught);
    - the string `skill-cefailures` appears nowhere in `AGENTS.md`, `README.md`, `skills/`,
      `.claude-plugin/`, or `.codex-plugin/`;
    - **positive check:** each of the four lifecycle gates references `documentation-sync` — i.e. the
      string appears in both `task-lifecycle.md` and `epic-lifecycle.md` (guards that the rewire
      actually landed, not just that the old ref is gone).
    This is the runnable check for the rewire — `tcw validate` only resolves `tcw://` markdown links,
    so it would not catch a dangling or missing skill reference.
    (Not adding content-shape assertions on the skill prose itself — skills carry no required `tcw://`
    syntax, so asserting that would be testing prose. YAGNI.)

## Phase 4 — Documentation Sync (self-application)

11. `docs/changelogs/upcoming.md` [Any-Code-Change] — add entries (with commit hash range):
    - Added: TCW-owned `documentation-sync` skill (+ references).
    - Changed: doc-sync now sourced from TCW instead of `skill-cefailures`; tcw-work lifecycle invokes
      it at plan + completion gates; README / codex manifest skill list.
12. `README.md` [Public-API] — already updated in Phase 2 (skills list). No separate task.
13. `docs/release-notes/upcoming.md` [Public-API] — evaluate; this is agent-facing, not end-user CLI
    behavior, so most likely **no** entry. Add a one-liner only if a user-facing note is warranted.

## Phase 5 — Verify

Run and confirm green. Note the negative greps (absence) and positive greps (landed) — the change can
pass all absence checks while a rewire was silently skipped, so both directions matter:

- `pytest -q` (config: `[tool.pytest.ini_options]`, `testpaths=["tests"]`) — full suite incl. the new guard.
- `tcw validate` — passes.
- **Absence:** `grep -rn "skill-cefailures" AGENTS.md skills/ README.md .claude-plugin/ .codex-plugin/` — empty.
- **Absence:** `grep -rn "cut-version\|FOLLOWUPS" skills/documentation-sync/` — no `:cut-version` refs;
  `FOLLOWUPS` only if it's the single permitted "use `tcw work` instead" note (else empty).
- **Positive (rewire landed):** `grep -rn "documentation-sync" skills/tcw-work/references/` — expect
  the four gates (task plan + task closeout + epic plan + epic completion). This is the check that
  catches a forgotten gate, which no absence grep would.
- **Positive (count moved):** `grep -rn "five skills\|six skills" README.md .codex-plugin/plugin.json`
  — both now say "six", neither says "five".
- **Trigger-vocab reconciliation (spec's top risk):** confirm `SKILL.md`'s trigger reference documents
  `Skill-Driven-Component` (or the "projects may add named triggers" mechanism) so it agrees with
  `AGENTS.md:54`. Explicit check, not folded into a general re-read.
- Re-read `SKILL.md` once for overall internal consistency.

## Parallelization

Minimal and not worth subagents. Phase 1 must precede Phase 2 and Phase 3. Within Phase 2, files 4–9
are independent edits. Phase 4 after implementation settles. One agent, sequential, is the right call.

## Closeout notes (not part of implementation)

- **Version bump:** offer at closeout. This is a meaningful plugin addition — a `patch` (or `minor`)
  via `scripts/cut_version.py` is the likely call; user decides.
- **Separate-repo follow-up (confirmed timing):** as the **last step of closeout**, after everything
  else is finished, open a GitHub issue on `github.com/brocef/skill-cefailures` to remove/deprecate its
  `documentation-sync` skill.
