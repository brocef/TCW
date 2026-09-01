# A broken `work.path` is hidden when a repository is also declared

## What happens

A node with **both** a `work.path` pointing at a directory that exists but is not
a valid store, **and** a `work.repository` declaration that has not been
provisioned, is told only about the declaration:

```
$ tcw work list
tcw work: …/tcw-config.yaml: the work store is declared in …/nowhere.git but has
not been provisioned here; run `tcw provision` to obtain it

$ tcw validate
work check: …/tcw-config.yaml: the work store is declared in …/nowhere.git but
has not been provisioned here; run `tcw provision` to obtain it
1 problem(s).
```

There are **two** configuration problems and one is reported. `work.path` names a
directory missing its status folders, and nothing says so.

## Why it happens

`resolve_store` (`tcw/store/fs.py`) tries rule 1, catches the `ValueError` that
`_open_at` raises for the unusable local store, and falls through:

```python
try:                                                        # rule 1
    return store_cls._open_at(raw_root, …)
except ValueError:
    pass
```

The fall-through is correct — a declaration exists precisely so an unusable local
store is not the end of the story. What is lost is the *reason* rule 1 failed:
the exception is discarded rather than carried, so rule 3's
`StoreNotProvisioned` is the only thing the user ever sees.

## Why it is worth fixing

For `tcw work list` the current message is arguably right: `tcw provision` **is**
the action that gets a working store, so the advice is actionable even though it
is incomplete.

For **`tcw validate` it is not**. That command's entire job is to enumerate a
node's configuration problems, and it is silently reporting one of two. A user
who meant `work.path` to work — the orchestrator folder is right there, they just
mistyped it or lost a status folder — provisions instead, gets a second store,
and never learns the first one is broken. Child A's criterion 4 was specifically
that validation *distinguishes* the failure modes; this is the case where it
merges them.

## Shape of a fix, to be decided at spec

The information exists and is thrown away, so the fix is about carrying it, not
computing it. Two obvious shapes:

- **Carry the rule-1 failure into the rule-3 error.** `StoreNotProvisioned` grows
  a "and the configured `work.path` is not usable: …" clause when rule 1 failed
  for a reason other than "there is nothing there".
- **Have `validate` ask separately.** It already reports per component; it could
  check the configured local path independently of resolution, so both problems
  are listed as two problems.

The second is probably right for `validate` and the first for the command
surface, but that is a spec decision. Note that "the local path does not exist at
all" should stay silent — with a declaration present that is the *normal* case
this feature exists for, and reporting it would make every provisioned node noisy.
That distinction is the substance of the item.

## Notes

- Found by a `bllm review diff` pass on a slice of child C's diff, during the
  store-provisioning epic's closeout. It is **child A's** behaviour, not child
  C's, and predates both later children — four `codex exec` review rounds over
  child A did not surface it.
- Reproduced by hand before filing: a `work.path` directory containing only
  `backlog/`, alongside an unreachable declaration.
- Not reworked into any of the three children: all are `completed` and the
  release carrying them is tagged.
