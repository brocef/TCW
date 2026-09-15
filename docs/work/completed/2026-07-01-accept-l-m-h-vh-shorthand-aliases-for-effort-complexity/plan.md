# Plan — Accept L/M/H/VH shorthand aliases for --effort/--complexity

Small change; single sequential pass. No parallel phases.

## Phase 1 — Normalizer (source of truth)

`tcw/store/base.py`, next to `WORK_LEVELS` (~line 185):

```python
WORK_LEVEL_ALIASES = {"l": "low", "m": "medium", "h": "high", "vh": "very-high"}

def normalize_work_level(value: str) -> str:
    """Map effort/complexity input (canonical or L/M/H/VH shorthand, any case)
    onto a canonical WORK_LEVELS value; raise for anything else."""
    v = value.strip().lower()
    if v in WORK_LEVELS:
        return v
    if v in WORK_LEVEL_ALIASES:
        return WORK_LEVEL_ALIASES[v]
    raise argparse.ArgumentTypeError(
        f"invalid level '{value}'; choose from "
        f"{', '.join(WORK_LEVELS)} (or shorthand L/M/H/VH)"
    )
```

- Needs `import argparse` in `base.py` (check; add if absent).

## Phase 2 — Wire into the CLI

`tcw/work/cli.py`:
- Import `normalize_work_level` alongside `WORK_LEVELS` (line 8).
- Replace `choices=WORK_LEVELS` with `type=normalize_work_level` on all 4 lines
  (426, 427, 462, 463); append " (L/M/H/VH shorthand ok)" to each help string.

## Phase 3 — Test

Add a focused test (pytest) covering: alias → canonical, case-insensitivity,
canonical passthrough, and invalid input raising. Put it next to the existing
work-store/CLI tests (locate with `ls tests/`).

## Phase 4 — Docs sync

Evaluate triggers:
- `docs/changelogs/upcoming.md` [Any-Code-Change] — add entry.
- `docs/release-notes/upcoming.md` [Public-API] — user-facing CLI behavior changed; add plain entry.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — check whether it documents `--effort/--complexity` values; add alias note only if it lists them.
- `README.md` [Public-API] — same check; update only if it enumerates the flag values.
- Capability body wording added at completion via the ledger flip (tcw-capabilities), not here.

## Verification

- `python -m pytest tests/ -q`
- `tcw work new "smoke" --effort h --complexity vh` → `tcw work show smoke*` shows `high`/`very-high`; then delete the smoke item.
- `tcw work new "smoke2" --effort s` → errors cleanly.
- `tcw capabilities check` (exit 0).

## Touch points

`tcw/store/base.py`, `tcw/work/cli.py`, `tests/`, `docs/changelogs/upcoming.md`,
`docs/release-notes/upcoming.md`, possibly `skills/tcw-work/SKILL.md` / `README.md`.
