# Outcome — A checkout value crashes every command, and a transitive declaration error exits zero

## What shipped

1. **An unresolvable `repository.checkout` is a `StoreDeclarationError`.**
   `Path.expanduser()` raises `RuntimeError` for a `~name` that names no user —
   not `ValueError`, not `OSError`, so nothing on the path caught it. And
   `checkout_root` is not called only when provisioning: `_target_path` calls it
   during `_load_graph`, on every command, for every connected project that
   declares a repository. So one such value in one config produced a raw Python
   traceback out of `tcw validate`, `tcw work list` and anything else that opens
   the registry, from a value the parser had accepted.

   `_target_path` records it as a graph problem against the config that carried
   it, which is where the reader can fix it. That also closes the two silent
   consequences the review traced: the `except Exception` in
   `_declared_nodes_in_graph` was swallowing it and dropping that node's
   declarations, and the one guarding `starting_registry` was turning
   `resolved_outside` off entirely — re-cloning every project, including ones the
   checkout already had.

2. **`tcw provision` exits non-zero for a declaration error found on a node it
   obtained.** `run_provision` already returns 1 for a malformed
   `connected-projects` declaration on the starting graph, with the comment *"a
   declaration that is present and wrong refuses, rather than reading as 'nothing
   declared' and reporting success"*. `enqueue` printed the identical problems
   and never set `failed`. A declaration that is present and wrong is present and
   wrong wherever it was found.

## Tests

Two new tests in `tests/test_store_provisioning.py`, both confirmed to fail
beforehand:

- a node whose only defect is `checkout: "~nosuchuser12345/away"` — asserting
  `FsProjectRegistry.check()` *returns* rather than raises, that the problem
  names both `repository.checkout` and the offending value, and that `validate`
  reports it. Before, every one of those calls raised.
- the same malformed `connected-projects` entry placed on a node fetched during
  the walk, asserting exit 1 and the message on stderr. The pre-change run
  printed exactly that message and exited 0, which is why the test asserts the
  exit code and the message separately.

```
$ python -m pytest -q -p no:randomly tests/test_store_provisioning.py \
      tests/test_project_registry.py tests/test_multiproject.py \
      tests/test_validate.py tests/test_retention.py tests/test_epic_completable.py
155 passed
```

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted. Both findings
were reproduced by the review and re-reproduced here as tests.

1. **Whether to catch `RuntimeError` at `checkout_root` or at every caller.** At
   `checkout_root`. It is the only place that calls `expanduser`, the failure is
   a property of the declaration rather than of any caller, and translating it
   into the declaration-error type the callers already handle means no caller
   needs to know `expanduser` exists.
2. **Whether to make the value a parse-time error instead.**
   `parse_repository_declaration` could reject a `~` it cannot resolve, but that
   makes a declaration's validity depend on which machine parses it — the exact
   coupling the whole feature exists to avoid. A config naming a home directory
   that exists on the author's machine is not malformed; it is unusable *here*,
   which is what the resolution error says.

## Notes

The bounding of `checkout` against escaping to an arbitrary directory — the other
half of what the review found in this area — is deliberately not here. It is a
design question about what a transitively discovered config may name at all, and
it is already filed as
`2026-09-04-tcw-provision-cannot-be-scoped-and-a-third-hop-config-can-name-a-checkout-directory`.
