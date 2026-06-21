# Plan

Baseline: `37e3984`.

1. **CLI** (`tcw/work/cli.py`):
   - `_new`: after `print(item.slug)`, if `not args.epic`, print start-hint to stderr.
   - `_start`: after each `started …` line (plain + worktree), print complete-hint to stderr.
2. **Tests** (`tests/test_work.py`): assert `new` emits the start-hint on `.err` and
   the bare slug on `.out`; assert `start` emits the complete-hint on `.err`; assert
   `new --epic` does *not* emit the start-hint.
3. **Skill** (`skills/tcw-work/SKILL.md`): rewrite the lifecycle-handshake lead into
   imperative trigger cues + self-check; keep per-command bullets.
4. **Verify**: `pytest -q`.
5. **Docs sync**: changelog (CLI behavior change → `Changed`/`Internal`); skill is the
   change itself. README/release-notes — judge: a new stderr hint is arguably
   user-visible CLI behavior → small release-note + README mention if warranted.
6. **Complete**: `tcw work complete <slug> --resolution done --confirm` (no capabilities).
