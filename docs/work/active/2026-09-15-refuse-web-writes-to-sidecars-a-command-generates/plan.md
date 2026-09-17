# Plan: Refuse web writes to sidecars a command generates

Small change; compressed plan, sequential, on `main`. Code edits wait until no
suite run is in progress in the checkout.

## Task 1 — tests first

- Modify `tests/test_serve_write.py`: new test beside the sidecar round-trip test
  (`:589`), with strict mode off — `PUT` of `rollup.md` and of `tracker.yaml` each
  return 409, the body names `tcw work reconcile` / `tcw work tracker`, and the item
  folder is byte-identical afterwards (criterion 1). Also assert the discovery
  endpoint still reports `generated` true/true/false (criterion 4).
- Modify `tests/test_tracker_strict.py::test_serve_refuses_what_it_cannot_check_and_changes_nothing`:
  move the `tracker.yaml` `PUT` out of the `strict tracker mode` list and assert it
  is 409 with the generated-sidecar message (criterion 2).
- Run both files: the new assertions fail, for the right reason.

## Task 2 — the refusal

- Modify `tcw/store/base.py` `WORK_SIDECARS`: `generated` values become
  `"tcw work reconcile"` and `"tcw work tracker import, link or unlink"`; the
  comment says the value names the owning command.
- Modify `tcw/serve/__init__.py`:
    - `PUT` route: after the registered-name check,
      `if (owner := WORK_SIDECARS[name].get("generated")):` send 409 via `_send_err`
      with `f"{name} is written by `{owner}`, not edited; run that command instead."`
      and return;
    - delete the `name == "tracker.yaml"` strict check and `_strict_refuses`'s
      `"tracker.yaml"` branch.
- Proof: criteria 1-5 by `pytest tests/test_serve_write.py tests/test_tracker_strict.py`
  and the grep; mutation check by deleting the new refusal and watching the new test
  go red.

## Task 3 — full suite (`pytest -q`).

## Documentation Sync

- `docs/changelogs/upcoming.md` [Any-Code-Change] — fires: Fixed entry.
- `docs/release-notes/upcoming.md` [Public-API] — fires, lightly: one line saying
  the web app's server now refuses edits to generated files.
- `README.md` [Public-API] — check its web app section for a claim about generated
  files; expected no change.
- `docs/guide/web-viewer.md` — not a configured entry; check for the same claim.
- `docs/guide/jira.md` [Tracker-Change] — check for a statement that the web app
  refuses `tracker.yaml` only under strict mode; update if present.
- Skills and `configure` references — do not fire.
- Capability `web/editing` — update the paragraph the spec names; declare it under
  `changed:` in this item's `capabilities.yaml`.

## Verification

Hands-on: start `tcw serve` against a scratch project, `curl -X PUT` both sidecars
and `capabilities.yaml`, and read the responses.
