# Hold one lock on the work store for every transition, not only the resolving ones

## Origin

GitHub issue [#73](https://github.com/brocef/TCW/issues/73), filed 2026-09-29 by @brocef.

> Status moves (`start`, `submit`, `rework`, `complete`) commit into the work store's repository automatically. When several agent sessions share one work store, those commits can collide with each other and with the sessions' own commits. Examples of a collision: a `.git/index.lock` failure, or one session's staged files swept into another session's commit.
>
> In a real run of three concurrent sessions (tcw 2.6.4), the only thing that prevented this was an external lock. Every state-changing `tcw` command and every hand commit in that repository was wrapped in a `mkdir`-based lock script. It worked, with no collision seen once it was in place, but it costs a wrapper around almost every command, and each new agent has to be told about it.
>
> **Asked for:** tcw takes its own short lock on the work store for the length of a transition (for example, a lock file under the store's `.git` directory), with a bounded wait and a clear message on timeout. It should also commit only the paths it wrote (`git commit -- <paths>`) rather than whatever the index holds. The second change matters even without a lock, because the index is shared across sessions (see also the issue about `new` leaving files staged).

## Triage notes

Checked against the code at v2.6.5, which narrows the ask:

- Transition commits are already limited to the paths the transition touched (`tcw/store/fs.py`, the scoped `git commit -- <paths>`), so the second ask is largely met already for status moves. What is not covered is `work new` and `escalate`, which do not commit at all (#66).
- A lock already exists — `_graveyard_lock` in `tcw/store/fs.py`, an `flock` on a temp file keyed to the store — but `_effect_transition` takes it only when the target status is a resolved one. `start`, `submit` and `rework` run unlocked, and nothing waits on another session's `.git/index.lock`.
