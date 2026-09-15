# Make start --take-over recover an interrupted claim from the CLI and the web app

## What is wanted

The documented remedy for an interrupted claim should work when a user runs it.

When a process dies holding a claim, every read of the item says
`<slug> has an interrupted claim; use --take-over --owner <identity>`. Following that
advice prints the same message and exits 1. `_start` in `tcw/work/cli.py` reads the
item (`st.get`) as an argument to the `pre` hook runner, before `st.start` is called and
before `--take-over` is looked at; that read finds the interrupted claim and raises. The
store's take-over branch works when called directly, and its tests exercise the store
API, so nothing failed. A comment in `tcw/store/fs.py` beside `start` describes exactly
this trap and says why `start` itself avoids it.

**Decided with the maintainer at triage:** the web app is in scope. `tcw serve`'s start
action never passes take-over (or an owner), so it cannot recover either.

## Constraints

- **The `pre` hook must still run before anything changes.** The ordering is deliberate:
  a refusing `pre` hook has to mean nothing happened. A fix that moves the read after
  `st.start` trades this bug for that one.
- **Check what else is evaluated early.** `st.get` is one of several arguments computed
  for the hook runner, and another `st.get` a few lines later would hit the same error;
  the others may have preconditions of their own.

## Notes

- Checked at triage on `main`: still present (`cli.py` evaluates `st.get(bare)` in the
  `run_pre(...)` call outside the `try` around `st.start`; `tcw/serve/__init__.py` calls
  `work.start(slug, force=force)` only).
- The same early `st.get` is what makes the absolute-slug case unreachable from the
  command line — one mechanism that blocks an attack and blocks the remedy.
- Reference material: asked; none provided.

## References

- `docs/work/completed/2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it/` —
  its verification found this, and its spec records the same `st.get` call from the
  other side.
- `tests/test_external_work_store.py` — covers the store's take-over branch directly.
