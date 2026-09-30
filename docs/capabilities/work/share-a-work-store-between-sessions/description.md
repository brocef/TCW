As a user, I can run several agents or terminals against one work store on one
machine — in the same checkout or in worktrees of it — and each `tcw work`
command that writes (every transition, a claim, creating an item, recording or
removing a resolved item) keeps its own changes and its own commit. I need no
lock of my own around `tcw`.

TCW holds one lock per store while a command checks, writes and commits. It
lives in the repository's git folder, so every session and worktree shares it
whatever its temp folder is, and nothing appears in `git status`. A
transition that waits more than 30 seconds gives up, changes nothing, and names
the process holding the lock; creating an item that has to wait that long
leaves the new item written but uncommitted and tells me to commit it. The slow parts — fetching and pushing a published store,
hooks, tracker calls, and a worktree's merge-back — run outside it, so one
session's slow network never holds up another's `start`.

Git run by something else can still hold the index for a moment. A TCW command
waits up to two seconds for another process's `index.lock` to go, and if it
stays, says so and that a lock a crashed git left behind has to be deleted by
hand.

Two clones on two machines are not covered: they meet in a git merge, as they
always have.
