# Plan — `load_yaml`'s broken mapping contract

Three production changes across two files. Tests first at each, because all three
defects are silent-or-crashing behaviour that no existing test noticed.

## Tasks

### Task 1 — failing tests for the loader contract

Modifies `tests/test_environment_hardness.py`, which already owns `load_yaml`
cases. Covers spec criteria 1 to 3:

- `[]`, `false`, `0` and `- a` each raise `yaml.YAMLError`, and the message names
  the path and the type found.
- absent, empty and `null` each return `{}`.
- a mapping returns unchanged, including a literal `{}`.

**Proves it:** the four raising cases fail now — three return `{}` and one
returns a list. Read each failure rather than assuming; the falsy three and the
truthy one fail differently, which is the whole shape of the defect.

### Task 2 — the loader

Modifies `tcw/store/fs.py:1068-1074`:

```python
if data is None:
    return {}
if not isinstance(data, dict):
    raise yaml.YAMLError(f"{path}: expected a mapping, found {type(data).__name__}")
return data
```

Docstring rewritten: it currently claims a contract the code does not keep, and
must say what raises. Name `yaml.YAMLError` as the deliberate choice and why —
ten sites already catch it.

**Proves it:** Task 1 goes green.

### Task 3 — the uncaught call sites, by hand

Changes nothing by itself. There are 31 call sites; ten are inside an existing
`except yaml.YAMLError`. **Every other one is read and classified**: does an
exception here reach a user as a message, or as a traceback?

Record the classification in `outcome.md` as a table. Any site that would
traceback gets a catch, and that is a change to `tcw/cli.py` or `tcw/store/fs.py`
decided per site — not predicted here, because the point of the task is to look.

**Proves it:** the table, and criterion 4 for the `init` path specifically.

### Task 4 — `validate` parses everything, and shape-checks what TCW owns

Modifies `tcw/validate.py:269-275`.

The existing loop must keep accepting any shape, so it parses directly instead of
through `load_yaml` — `docs/work/dod.yaml` is a legitimate top-level list and an
inbox attachment may be anything. Alongside it, a file whose name is one of

`state.yaml` · `meta.yaml` · `capabilities.yaml` · `graveyard.yaml` · `config.yaml`

is reported when it parses to anything but a mapping.

Tests first, covering criteria 6 to 8: a `state.yaml` of `[]` and of `- a` each
make `validate` exit non-zero naming the file; this repository still validates
clean; a `*.yaml` attachment holding a list does not fail.

**Proves it:** `tcw validate` on this repository exits 0 — 372 owned files, all
mappings, plus `dod.yaml` which is not owned.

### Task 5 — the contract in the abstract store

Modifies `tcw/store/base.py`. The rule "a malformed record reads as empty, and
validation reports it" is store-wide, not a filesystem detail — another backend
states it as a row failing its schema check. It goes on the abstract store's
validate operation, where a second implementation would read it.

Parsing YAML stays in the adapter. This is the prime directive's split, applied.

**Proves it:** read it.

### Task 6 — end-to-end, by hand

Changes nothing. Reproduces all three defects on scratch nodes before and after,
through the CLI:

- `printf '[]\n' > tcw-config.yaml && tcw init --id demo` — exits non-zero, file
  byte-identical. Compare a hash before and after, not just the content.
- a `state.yaml` of `- a` — `tcw work list` lists the item, no traceback.
- a `state.yaml` of `[]` — `tcw validate` names it.

## Documentation Sync

- **`README.md` — [Public-API].** Fires: user-facing behaviour changes, since
  `tcw validate` can now fail where it passed. But the README does not document
  validate's failure modes — it links to the guide. Evaluated, not edited.
- **`docs/release-notes/upcoming.md` — [Public-API].** Fires. Must lead with the
  corrupt-item-reads-as-healthy case, and warn that `validate` may newly fail on
  a node that was passing, which is the point rather than a regression.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change].** Fires. `Fixed`, three
  entries, and `Changed` for the loader contract.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component].** Fires: `validate`
  reports a new class of problem, and eight skill files mention `tcw validate`.
  Each is read; most describe *running* it rather than what it reports, so most
  are expected to need nothing. Recorded either way.
- **`docs/guide/linking-and-validation.md`**, not a declared entry but the prose
  home for `tcw validate` — read and updated if it enumerates what validate
  checks.

## Verification

What the suite cannot check:

- **Whether any of the 21 uncaught call sites turns a corrupt file into a
  traceback.** Task 3 is reading, and reading can miss. After it, grep the CLI
  for commands that touch YAML and run each against a node with a corrupt
  `state.yaml` and a corrupt `tcw-config.yaml`. Report what was run.
- **Whether the owned-name set is complete.** It is a judgment. List every YAML
  filename TCW writes, by grepping `dump_yaml` and `write_text` call sites, and
  compare against the set.
- **That `validate` is still useful.** A check that fires on a healthy repository
  is worse than none. Criterion 7 is the guard, and this repository with 372
  owned files is a real sample.

## Notes

- Task 3 is the one that could grow. If it finds several sites needing catches,
  that is the finding, and it is reported rather than absorbed silently.
- No task depends on another except 2 on 1 and 4's implementation on its own
  tests. The suite is green at every commit boundary but the two deliberate reds.
