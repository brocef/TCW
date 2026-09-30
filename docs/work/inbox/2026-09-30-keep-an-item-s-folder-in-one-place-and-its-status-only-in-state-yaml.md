# Keep an item's folder in one place, and its status only in state.yaml

Follow-up from #58 (a stale item path), deferred there as a non-goal.

Every transition moves the item's folder (`active/<slug>/` → `review/<slug>/`),
so any path noted before a transition goes stale, and a write through it makes
a stray folder. #58 made that loud: `complete` needs `refined-outcome.md`, and
`validate` reports strays. The issue's follow-up comment suggests removing the
cause instead: the folder never moves, and the status lives only in
`state.yaml`.

That changes the store's layout — every reader that infers status from the
folder, `.gitignore` rules for resolved folders, retention, and every existing
project on disk — so it needs its own spec and a migration.
