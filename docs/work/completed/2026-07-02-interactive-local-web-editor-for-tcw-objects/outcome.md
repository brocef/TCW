# Outcome — Interactive local web editor for TCW objects

**Work completed successfully.** All five planned phases were implemented by the
local LLM agent (`bllm-agent`, Qwen3.6-27B), one phase per invocation, each
verified before the next was dispatched. Implementation lives on branch
`interactive-local-web-editor`. The item is **not yet completed** — it is held at
the verification/refinement gate pending user sign-off and closeout decisions.

## What changed

Per-phase, each committed as a checkpoint on the branch:

- **Phase 1 — Store contracts & validation** (`14371ca`). Abstract store edit
  surfaces on the ABCs: `create_work`/`update_work` (composite, prevalidated,
  partial-merge), `read/write_artifact`, `read/write_sidecar`, `get_detail`;
  `update_term`; `update_capability`, `add_entry`. Per-editable-resource opaque
  revision tokens + `StaleRevision`. Registries `WORK_SIDECARS`,
  `TAXONOMY_EDITABLE_FIELDS`. FS adapter: content-hash tokens, temp-file + atomic
  replace, validate-before-persist. CLI `work new`/`edit` refactored onto the
  shared store methods. +77 store tests → 320 passing.
- **Phase 2 — Write API** (`481d143`). `do_PATCH`/`do_PUT`/`do_DELETE` +
  resource-oriented routes for all three axes, calling the Phase 1 store methods
  (no `docs/` path logic in `serve`). Revision-bearing detail reads, sidecar
  discovery, JSON envelopes, `MAX_BODY_BYTES` (1 MiB) pre-parse guard, local-CSRF
  / DNS-rebind defense (JSON-only + loopback `Host`/`Origin`), stale 409,
  deterministic exception→status mapping, single-decode percent-encoded refs.
  +101 API tests → 421 passing.
- **Phase 3 — Frontend editor architecture** (`2209aad`). Reusable editor
  framework in `app.js` (247→995 lines): view/edit/create/dirty/saving/error
  state machine, raw-Markdown textarea + live `marked.js` preview, revision
  tokens in editor state with 409 conflict recovery (draft preserved), and
  `beforeunload` + app-level dirty-navigation guards. Work axis wired as the
  proving slice. No new deps/build/CDN; CSP intact; `esc()` escaping preserved.
- **Phase 4 — Axis-specific UI flows** (`e06c3d7`). All three axes' create/edit
  forms + lifecycle-action modals: work create/edit (all fields), artifact +
  `capabilities.yaml` sidecar editors, start/complete/drop shown only where
  legal. Complete is an in-page modal requiring resolution + all DoD acks + the
  capabilities reconciliation reminder, with inline blocker/force handling.
  Taxonomy + capability create/edit with post-write `check()` warnings surfaced.
  Two bounded backend additions: `dodChecklist` in work detail; `warnings` in
  taxonomy/capability write responses. +6 tests → 427 passing.
- **Phase 5 — Verification & docs** (uncommitted at time of writing). Updated
  `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`
  (range `14371ca..HEAD`), and the `tcw-work`/`tcw-capabilities`/`tcw-taxonomy`
  driving skills.

## Verification performed

- **Full test suite: 427 passing** (243 baseline + 184 new), re-run by the
  orchestrator after each phase; 0 regressions.
- `tcw taxonomy check` → OK; `tcw capabilities check` → OK.
- **Write-path end-to-end smoke (10/10)** against a live server on a throwaway
  node: detail-read carries a revision; PATCH with fresh revision persists and
  rotates the token; stale PATCH → 409 with no write; non-JSON `Content-Type`
  rejected; non-loopback `Origin` rejected; artifact PUT round-trips.
- `node --check tcw/serve/static/app.js` clean; no `eval`/inline handlers;
  `esc()` used throughout; CSP `default-src 'self'` unchanged.
- **documentation-sync** gate: all four fired triggers (README, release notes,
  changelog, three driving skills) updated.
- **Dual review** (subagent code review + `bllm-review-many` on the backend)
  found real defects the per-phase test gate missed. Litmus test: **clean** (no
  FS-only method leaked onto the ABCs). Confirmed defects (verified against code):
  - **High #1 — UI blockers corrupted.** `app.js` sends blockers as objects
    (`{slug: ref}`) but `create_work`/`update_work` expect `list[str]` and call
    `_entry_for(ref)`; every blocker set via the browser is stored malformed and
    the blocking edge is dropped. (Store tests passed because they send strings.)
  - **High #2 — `update_work` parent-move data loss.** On a simultaneous parent +
    body change, `body_path` is not recomputed after the folder move, so the new
    body is written to the abandoned old directory (lost), the moved item keeps
    its old body, the emptied source dir is never removed, and the move isn't
    git-staged. Untested path; a stub `pass`/rambling comments mark it half-baked.
  - **Med/High #3 — path traversal.** `add_entry` (`collection`) and taxonomy
    `add` (`slug`) join caller input into store paths without sanitizing `..`/
    absolute paths (CSRF-gated, so local-only, but violates the bounded-input spec).
  - **Med #4 — `/open` POST bypasses the CSRF/loopback guard** (pre-existing from
    the read-only viewer): it runs before `_validate_mutating_request`.
  - **Med #5 — `add_entry` appends duplicate capabilities** instead of failing on
    a name collision (spec item 11).
  - Accepted/deferred (Low): #6 `marked.parse` relies on CSP for XSS (per the
    preserve-CSP constraint); #7 IPv6 `[::1]` Host fails closed + drop `0.0.0.0`
    from loopback set + optional GET Host check; #8 server `complete` doesn't
    enforce DoD completeness (pre-existing store semantics; UI enforces); #9
    multi-file create/update not transactional on mid-write I/O failure; #10
    capability revision token is file-scoped (spurious 409 between co-located caps).

## Deviations from plan.md

- **Phase 3 agent stopped near the end.** The `bllm-agent` run was killed during
  its final report, but the code was already complete and valid (`node --check`
  clean, file ended cleanly, smoke checklist present). Kept and verified per user
  decision ("keep and verify").
- **Dead duplicate removed during Phase 4 verification.** The agent left an
  abandoned first attempt at `showCompleteModal` (shadowed by the working copy).
  The orchestrator deleted the dead block (63 lines) — a safe, behavior-preserving
  cleanup.
- **Native `confirm()` for the dirty-navigation guard** (introduced in Phase 3).
  Functionally satisfies "warn on dirty nav," but deviates from the
  no-native-dialogs preference and would block browser-automation. Flagged for
  the user; not yet changed.
- **Live in-browser click-through deferred.** The Chrome extension was not
  connected, so the actual rendering of forms/modals was not eyeballed in a real
  browser. The full write stack the UI depends on was instead verified via the
  API smoke above. Plan item 5.11 already scheduled a browser pass; still
  recommended before/at closeout.
- **Capability flip and version bump intentionally NOT done.** `web/editing#edit-
  tcw-content-in-a-local-web-app` remains `Missing`; no version bump. These are
  closeout decisions awaiting user approval.

## Follow-up notes (not yet TCW items — closeout decision)

- Decide `confirm()` → in-page modal for the two dirty-nav prompts (or keep).
- Live browser click-through of create/edit/complete/drop across all three axes.
- Rich Markdown editor is already tracked separately:
  `2026-07-02-add-a-vendored-rich-markdown-editor-to-the-local-web-app`.

## Post-review fixes (applied in-session after the dual review)

All confirmed High/Med findings fixed, each with a regression test (full suite
**436 passing**):

- **#1 blockers** — `app.js` now sends blocker refs as plain strings (edit + create
  paths); `create_work`/`update_work` reject non-string refs so a bad client fails
  loudly instead of storing malformed `{external: {slug…}}`. Tests: reject non-string
  blocker (create + update).
- **#2 parent-move** — `update_work` validates the parent target, writes state/body
  to the current location, then effects the re-parent as a single git-aware folder
  move (`self._mv`) that carries nested children and leaves no orphan; rejects
  nesting under self/descendant. Tests: body-edit-preserved-on-reparent, denest,
  self/descendant rejection.
- **#3 traversal** — new `_safe_store_id()` rejects `..`/absolute/backslash inputs;
  applied to `add_entry(collection)` and taxonomy `add(slug/parent)`. Tests: traversal
  rejected for capability collection and taxonomy slug.
- **#4 `/open` guard** — `_validate_mutating_request` now runs for ALL POSTs before
  the `/open` dispatch; the frontend opener sends `Content-Type: application/json`.
  Test: non-JSON `/open` rejected, opener not spawned.
- **#5 duplicate capability** — `add_entry` refuses a heading that already exists in
  the collection. Test: duplicate add rejected.
- Minor hardening: dropped `0.0.0.0` from the loopback set; fixed IPv6 `[::1]` Host
  parsing.

Low findings #6/#8/#9/#10 accepted for v1 as noted above.
