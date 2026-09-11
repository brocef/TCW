# Spec — `load_yaml` reads a falsy document as an empty mapping

## Capability changes

None. No command gains or loses a documented behaviour. Three commands stop
lying about a corrupt file, which is a defect removed rather than a capability
changed.

## Problem

`load_yaml` (`tcw/store/fs.py:1068-1074`) ends in `return data or {}`. Its
annotation says `-> dict` and its docstring says "Load a YAML mapping (empty
dict if the file is absent/empty)". **Neither is true.** A falsy document is
silently turned into a mapping; a truthy non-mapping is returned unchanged.

| Document | `yaml.safe_load` | `load_yaml` |
| --- | --- | --- |
| absent, empty, `null` | — / `None` | `{}` |
| `[]`, `false`, `0` | `[]`, `False`, `0` | **`{}`** |
| `- a` | `['a']` | **`['a']`** |

The intake reports only the first half of this, on `tcw-config.yaml`, and calls
it "indistinguishable from an empty or absent file". Reproduced at `31241b5c`,
the consequences are worse and reach three commands.

### A. A falsy config is silently overwritten

```
$ printf '[]\n' > tcw-config.yaml && tcw init --id demo
.gitignore: resolved work (completed/, discarded/) stays on disk…
$ cat tcw-config.yaml
id: demo
```

The user's file is gone without a word. The same file containing `- a` is
refused — `config must be a mapping` — and left alone. The guard exists at
`fs.py:157` and `:869`; the coercion walks past it.

### B. A corrupt item reads as healthy, and `tcw validate` agrees

With a work item's `state.yaml` replaced by `[]`:

```
$ tcw work show 2026-09-11-real
2026-09-11-real  [backlog]
title: 2026-09-11-real          ← fabricated from the directory name
$ tcw validate
validate OK
```

Nothing anywhere reports that the item's state file is not a state file.

### C. A truthy non-mapping takes the whole board down

With the same file replaced by `- a`:

```
$ tcw work list
AttributeError: 'list' object has no attribute 'get'   (fs.py:4063)
```

`tcw work show` and `tcw validate` crash identically. **One malformed item makes
the board unreadable**, which is exactly what `_safe_yaml` (`fs.py:4023`) exists
to prevent — its docstring says "a malformed state file degrades to empty rather
than crashing the board". It catches `yaml.YAMLError`, and a well-formed
non-mapping never raises one, so the tolerance it promises has never applied to
this case.

## Goals

1. `load_yaml` means what it says: a mapping, or `{}` for a document that is
   absent or has no content.
2. A malformed state file degrades rather than crashing the board — the
   behaviour `_safe_yaml` already promises.
3. `tcw validate` reports a TCW-owned YAML file that is not a mapping, rather
   than passing it or crashing on it.
4. A malformed `tcw-config.yaml` is refused rather than overwritten, whatever
   shape it is.

## Non-goals

- **Schema validation.** Whether a `state.yaml` has the right *keys* is a
  different question. This is about the document being a mapping at all.
- **Rejecting an empty `state.yaml`.** An empty document stays `{}`. Treating
  "present but empty" as incomplete would need a schema rule, which is the
  non-goal above.
- **Distinguishing `null` from an empty document.** Both parse to `None` and
  both mean "no content". Separating them would need to inspect the raw text,
  and no caller wants the distinction.
- **Making `tcw serve` or attachments stricter.** An attachment may hold any
  YAML a user likes; only files TCW writes are held to the mapping contract.

## Design

Three changes.

### 1. `load_yaml` raises on a non-mapping

```python
if data is None:
    return {}
if not isinstance(data, dict):
    raise yaml.YAMLError(f"{path}: expected a mapping, found {type(data).__name__}")
return data
```

**`yaml.YAMLError`, not `ValueError`, and that choice is the whole design.** Ten
sites in `fs.py` already catch `yaml.YAMLError` around a load, including
`_safe_yaml` (`:4023`), `_read_item`'s capability read (`:4059`), `:4326` and
`:4959`. Raising the type they already expect means **C is fixed at every one of
them with no per-site edit**: a `- a` state file now degrades to `{}` and the
board lists the item instead of crashing. A `ValueError` would leave C crashing
in different clothes.

There are **31 call sites**, 28 in `tcw/store/fs.py` and 3 in
`tcw/validate.py`. None of the 28 consumes a non-mapping as its data contract.

### 2. `validate`'s YAML pass keeps parsing everything

`tcw/validate.py:269-275` scans every `*.yaml` under the doc trees purely for
syntax and duplicate keys, and discards the value. It must keep accepting any
shape: `docs/work/dod.yaml` is a legitimate top-level **list**, and an inbox
attachment may be anything. So that loop parses directly rather than through
`load_yaml`.

### 3. `validate` gains the shape check that is the point

The same pass reports a file TCW owns that is not a mapping. Owned by name:

`state.yaml` · `meta.yaml` · `capabilities.yaml` · `graveyard.yaml` ·
`config.yaml`

Every one of the 372 such files in this repository is a mapping today; `dod.yaml`
is the only YAML under the doc trees that is not, and it is not in the set.
Naming what TCW owns is narrower than exempting what it does not, and an
attachment called `state.yaml` is a case nobody has.

**This is what fixes B.** Change 1 alone does not: a `[]` state file would raise,
`_safe_yaml` would catch it, and the item would still show a fabricated title
with `validate` still reporting OK. That tolerance is correct and deliberate —
one corrupt item must not blank the board — so the report belongs in `validate`,
which is the command whose job is saying what is wrong.

### The contract is the store's, not the adapter's

Parsing YAML is a filesystem detail. **"A malformed record reads as empty, and
validation reports it" is not** — it is a store-wide rule another backend states
as a row failing its schema check. The rule goes in the abstract store's
docstring for the validate operation, not only in `fs.py`.

## Acceptance criteria

1. `load_yaml` on a file containing `[]`, `false`, `0` or `- a` raises
   `yaml.YAMLError` naming the path and the type found.
2. `load_yaml` on an absent, empty or `null` file returns `{}`.
3. `load_yaml` on a mapping returns it unchanged, including `{}` written
   literally.
4. **A.** `printf '[]\n' > tcw-config.yaml && tcw init --id demo` exits non-zero,
   prints a message naming the file, and **leaves the file byte-identical**.
   Same for `false`, `0` and `- a`.
5. **C.** With a `state.yaml` containing `- a`, `tcw work list` exits 0 and lists
   the item, `tcw work show <slug>` exits 0, and neither prints a traceback.
6. **B.** With a `state.yaml` containing `[]` or `- a`, `tcw validate` exits
   non-zero and names the file and the problem.
7. `tcw validate` still exits 0 on this repository, whose `docs/work/dod.yaml` is
   a top-level list.
8. A `*.yaml` attachment holding a list does not make `tcw validate` fail.
9. `pytest` passes with no fewer than the `2627` baseline.

## Risks

- **Turning a silent coercion into an exception is a behaviour change across 31
  call sites**, and the reason it is safe is that ten of them already catch the
  exception being raised. The ones that do *not* catch it are the ones that
  should fail — `init` reading a malformed sentinel. Each uncaught site is
  checked by hand rather than assumed.
- **The owned-name set is a judgment that will drift.** A future TCW-written YAML
  file added under a new name is silently outside the check. Mitigated only by
  putting the list in one place with a comment; a test asserting every
  `*.yaml` TCW writes is in the set would be better and is not attempted here.
- **`validate` gaining a new failure mode may turn a green node red**, which for
  this repository is criterion 7 and for a user is the point. A node that was
  passing while carrying a corrupt file was never really passing.
- **`_safe_yaml`'s tolerance now hides a real error from the board.** That is
  its job, and criterion 6 is what makes the error visible somewhere else. If
  `validate` is not run, a corrupt item still reads as healthy on the board —
  accepted, because the alternative is crashing.

## Notes

- Line citations are against `31241b5c`.
- The intake reports only shape A and only for `tcw-config.yaml`. B and C were
  found by running the commands, and both advisors independently agreed C
  belongs here: same function, same contract, and the fix for A removes it for
  free.
- **The advisors disagreed on which failure is worst and it did not change the
  work.** One ranked B first for falsely certifying corruption; the other put A
  alongside it for destroying evidence immediately. All three are fixed, so the
  ranking only decides what the release note leads with.
