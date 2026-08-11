As a user, I run `tcw work show <slug>` to read an item's state and body
(including any recorded blockers), `tcw work path <slug>` to print its current
on-disk path, or `tcw work path` without a slug to print the absolute, resolved,
configuration-aware work-store folder.
For initiative-related work, `show` includes the item's `type` and `initiative` fields when present so an agent can choose the right lifecycle path.
