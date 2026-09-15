# Refined outcome — Status filter toggle buttons in the serve web UI

## Verification decision

User verified the result and requested one refinement mid-flight — **per-status
colors** on both the toggle buttons and each work item (shipped, see `outcome.md`).
Then approved closeout: complete the item and cut a **patch**.

## Final verification evidence

- Browser drive: toggles + colored badges render and filter correctly; default
  hides completed; composes with text filter.
- `pytest tests/test_serve.py tests/test_serve_descendants.py` → 16 passed.

## Closeout choices

- **Completion route:** committed directly to `main` (repo convention).
- **Version:** patch bump (0.10.0 → 0.10.1) via `scripts/cut_version.py`.
- **Docs:** README `tcw serve` section, changelog, release notes updated.
- **Deferred (not TCW items):** persist toggle state across reloads; per-status
  counts on the toggles.
