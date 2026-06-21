# Plan

Doc refactor only — no code, no tests. Baseline: `5ddaa20`.

1. **Create `skills/tcw-work/docs/`** with three files, moving the sections
   verbatim (lightly de-duplicating cross-references):
   - `process-inbox.md` ← current SKILL.md lines 10–19
   - `decompose.md` ← lines 38–62 ("Keep items small")
   - `cross-node-epic.md` ← lines 64–93 + the "Which path?" paragraph
2. **Rewrite `skills/tcw-work/SKILL.md`** as the router: keep intro, planning,
   lifecycle handshake, resume, quick-ref; replace the three moved sections with a
   "Sub-procedures (read on demand)" block of gated pointers.
3. **Verify no loss** — `wc -l` the four files; eyeball that router + docs ≥ old
   content; confirm relative links resolve (files exist).
4. **AGENTS.md** — add a short "Skill authoring" note: router + gated `docs/`,
   core judgment inline, rare sub-procedures deferred.
5. **Changelog** — `docs/changelogs/upcoming.md` Internal entry (skill restructure,
   hash range from `5ddaa20`). Skip README + release-notes (no user-facing change).
6. **Documentation Sync** — run the `documentation-sync` skill to confirm only the
   skill files + changelog + AGENTS.md fire; nothing else.
7. **Complete** — `tcw work complete <slug> --resolution done --confirm` (no
   capabilities to reconcile — no product delta).
