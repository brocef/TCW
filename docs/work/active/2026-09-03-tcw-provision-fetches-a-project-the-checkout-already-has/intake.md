Found while configuring the Proposit repositories against the finished
node-provisioning work, on 2026-09-03. Reproduced, not theorised.

Standing in `proposit-app/apps/server` with only that repository on disk:

    $ tcw provision --dry-run
      proposit-app: already available at …/proposit-orchestration-73cbcd814e44
    → proposit-core: https://github.com/Proposit-App/proposit-core.git at main → …
    → proposit-app-repo: https://github.com/Proposit-App/proposit-app.git at main → …
      proposit-app-repo: would obtain into …-proposit-app-7df9029374a6

The last two lines are a second clone of the repository the command is being run
from. The orchestration node declares where each of its children comes from —
correctly, since a session starting from *it* would need them — and the walk
obtains every declaration it meets without asking whether that project is
already here.

`proposit-app-repo` is present, reachable, and the current node's own ancestor.
Fetching it again wastes a clone, puts a second copy of the same project in the
graph under one id, and is exactly the "a store that is already here always
wins" rule not being applied to nodes.
