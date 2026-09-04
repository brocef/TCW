# Outcome — The retention operations the CLI calls are not on the abstract work store

## What shipped

Seven operations move onto `WorkStore`: `retention`, `retention_problems`,
`retention_conflicts`, `pending_deletion`, `pending_removal`, `delete_resolved`
and `describe_location`. They were defined only on `FsWorkStore` while the CLI
that calls them — `tcw work complete`, `tcw work delete`, `tcw work show`,
`tcw validate` — is storage-neutral, so a second adapter driven through the
completion path would have raised `AttributeError`.

This is an inconsistency inside one feature rather than a convention to follow:
`tombstone` and `record_tombstone`, the immediate neighbours, are already
abstract, and `parse_retention`'s own docstring makes the case for the whole
group — "a tracker-backed store can honor *do not retain resolved items* by
closing and dropping the ticket".

**Concrete, not abstract**, and every default describes an adapter that simply
does not do retention: it keeps everything, so nothing is ever pending and
`delete_resolved` is unreachable through the CLI. That is a legitimate
implementation rather than a stub — the same shape `incomplete_graph_note` uses —
and it makes adding retention to an adapter opt-in rather than a new obligation
on every one.

Two defaults carry a decision rather than a value:

- **`delete_resolved` raises `NotImplementedError`** naming the class, rather
  than returning something. There is no honest do-nothing answer to "remove this
  and tell me where it went", and the call is unreachable while `retention()`
  keeps everything, so an adapter reaching it has skipped the gate.
- **`describe_location` renders, and never resolves.** `Tombstone.location` is
  opaque and never parsed above the adapter, so the abstract form is "show this
  to a reader"; the contract it carries is only that a handle must not fail
  *silently*, which an adapter able to check its own handles honors by saying so.

## Tests

Two in `tests/test_retention.py`:

- the seven names are asserted present in `vars(WorkStore)`, which fails against
  the previous code;
- a minimal subclass with every abstract method stubbed exercises each default,
  including the `NotImplementedError`. Stubbing the abstract set rather than
  hand-writing thirty-five methods is what keeps this test from rotting as the
  interface grows — and it is what caught a misplaced `@abstractmethod` while
  this change was being written, which had silently made `retention` abstract and
  `record_tombstone` concrete.

```
$ python -m pytest -q -p no:randomly tests/
4 failed, 2373 passed in 354.98s (0:05:54)
```

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted. The prime
directive settles the "should these be on the interface" question directly, and
the intake had already quoted it.

1. **Abstract or concrete with defaults.** Concrete. Abstract would oblige every
   future adapter to implement retention before it could implement anything, and
   the litmus test asks whether an operation *could* be implemented elsewhere,
   not whether it must be. The defaults are also the honest description of an
   adapter that keeps everything, which is what the feature's documented default
   behaviour already is.
2. **What `delete_resolved`'s default should do.** Raise. Every alternative —
   returning `""`, returning the slug, doing nothing — is a claim that a removal
   happened.
3. **Whether to move `st.path()` too.** No. It has the same shape and predates
   this branch, so it is a different item's scope; noting it here rather than
   widening this one.

## Notes

The misplaced decorator is worth recording: inserting the block immediately above
`record_tombstone` put it between that method's `@abstractmethod` and its `def`,
so the decorator silently rebound to the first new method. Nothing failed except
the test that instantiates a minimal subclass — which is exactly why that test is
the one worth having.
