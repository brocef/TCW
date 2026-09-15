# Publish provisioned-store writes to their remote

## The request

Keep a provisioned store in step with the repository it came from, so work done
in an ephemeral environment is not lost when that environment goes away.

This is child C of
[the store-home-repository initiative](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it),
and the last of its three. From the initiative's own request:

> **Writes should stay in step with the remote.** A provisioned store should pull
> before and push after transitions, so a cloud session's work outlives the
> session. This is new territory: TCW performs no network writes today.

Children A and B made a declared store *reachable*. A cloud session can now clone
the code, run `tcw provision`, and read the board. What it cannot do is keep
anything it changes: `tcw work start`, `submit`, and `complete` commit into the
provisioned working copy, and that working copy is inside a container that gets
reclaimed. The board the session was given is real; the work it does on that
board is written to a disk nobody will see again.

## Decisions taken with the requester

Both were left open by the initiative spec and settled before this item's spec
was written.

- **Pull before, push after — as originally asked.** The alternative considered
  and rejected was push-only, leaving refresh to the existing explicit
  `tcw provision --refresh`. The requester chose the original shape: the
  strongest guarantee against a diverged remote, accepting that a transition on a
  published store becomes a network round-trip.
- **A publish failure reports loudly and rolls nothing back.** The command exits
  non-zero and says exactly what landed and what did not. It does not undo the
  transition.

These two are more coherent together than either is alone, because the halves
fail at different points in the sequence:

| Failure | State at that moment | Answer |
| --- | --- | --- |
| the pull fails | nothing has moved | refuse the transition cleanly; there is no partial state to explain |
| the push fails | the move and the commit have landed | report it, exit non-zero, change nothing back |

The asymmetry is not a special case: it is what "where did this break?" already
implies. And it follows a precedent already in the code. `_commit_transition`
(`tcw/store/fs.py:4204-4222`) refuses to roll back a landed `git mv` when the
commit fails, in those words:

> The move is never rolled back on a commit failure. The `git mv` already landed
> in both the index and the working tree, and undoing it introduces a second
> failure mode worse than the first — so the error says the item moved and the
> commit did not.

A failed push is the same situation one step further out, and gets the same
treatment for the same reason.

## The question the spec has to answer first

**Which stores publish?** The resolution ladder gives three ways a store can be
the one in use, and they are not equally obviously "published":

1. resolved from a declaration, at the provisioned location (ladder rule 2);
2. resolved from a local `<component>.path` **while** a `repository` block also
   exists (rule 1, declaration present but unused);
3. resolved with no declaration at all — an ordinary local store whose Git
   repository may nevertheless have an `origin`.

Case 3 must never publish. TCW would start pushing the user's own repository on
every status change, which nobody asked for and which would be a genuinely
alarming thing for a tool to begin doing.

Cases 1 and 2 are a real choice and belong in the spec, not here. Worth recording
now: under case 1 only, the requester's laptop — which has the orchestrator
folder and resolves through rule 1 — would not publish, while their cloud session
would. That asymmetry looks odd stated baldly, and is arguably right: the cloud
session is the one whose disk disappears.

## Constraints

- **Only this step and `tcw provision` may reach the network.** Initiative
  criterion 6 carves out exactly "the provisioning verb and the publish step child
  C adds to a transition". Pull-before makes that carve-out two steps rather than
  one, and it must not widen further — enforced in the shape of the package-wide
  rule in `tests/test_subprocess_stdin.py`.
- **There has to be a way to turn it off**, and it has to be discoverable. A user
  who cannot reach the remote, or does not want automatic pushes, needs an answer
  better than removing the declaration.
- **A store with no declaration behaves exactly as it does today.** No network,
  no new failure modes, no new configuration required.
- **Git is invoked with stdin closed**, as everywhere else, so a remote demanding
  credentials fails rather than hanging for input that will never come.

## Out of scope

- The provisioning verb's contract, the config schema, and `FsTreeStore.open` —
  children A and B own those, and this item consumes them unchanged.
- Merge-conflict *resolution*. Detecting divergence and reporting it actionably is
  in scope; automatically resolving a conflict in someone's work store is not.
- Replacing the filesystem store with a remote tracker, which remains tracked
  separately.

## Notes

- The initiative spec flags this as its own biggest risk, and the wording is worth
  keeping in front of whoever specs it: _"Child C puts a network hop inside a
  state machine that is currently local and atomic. Push failures, diverged
  remotes, and conflicts are new states for transitions that today either happen
  or don't."_
- **Instruction for the spec stage, carried from a post-mortem across children A
  and B:** four times across those two items, an acceptance criterion written as a
  general property was verified only against the handful of examples in its own
  text or fixtures, and the property went unchecked. Child B's spec tried to fix
  this by *wording* criteria as properties and it happened again anyway — the
  narrowing moved from the criterion text into the test fixtures. This item's
  failure modes (unreachable, refused, diverged, rejected, conflicted, partially
  applied) are exactly the shape that invites an enumeration. Whatever mechanism
  the post-mortem lands on applies here first.

## References

The initiative recorded "asked; none provided — the code is enough", and that
answer stands. What matters is in the repository:

- `tcw/store/fs.py` — `_effect_transition` (4154-4202) and `_commit_transition`
  (4204-4222). _Why:_ the sequence a publish step joins, and the rollback
  precedent it should follow.
- `tcw/store/base.py` — the epic spec's litmus table puts publication in the
  **store interface as a property of the store**, not as a verb on each
  transition. _Why:_ a tracker-backed store publishes by definition; only the FS
  adapter needs commit-and-push.
- `tcw/store/fs.py` — `FsStoreProvisioner._refresh` and `_require_declared_checkout`.
  _Why:_ the existing fetch path, and the check that a checkout's `origin` matches
  the declaration before contacting it — which a push needs at least as much.
- `tests/test_subprocess_stdin.py` — _Why:_ the package-wide rule that any new
  network call must satisfy.
