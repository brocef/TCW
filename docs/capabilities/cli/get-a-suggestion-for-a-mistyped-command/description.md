As a user, when I type a subcommand `tcw` does not have at that level, the error
still lists every valid choice, and adds one line naming the command I probably
meant. A word that exists one level down is named in full — typing *tcw tags
list*, with `work` left out, suggests `tcw work tags list` — a common synonym
points at the real verb (`status` → `show` or `list`; `info`, `view`, `get` and
`cat` → `show`; `ls` → `list`), and a near-miss spelling points at the closest
verbs (`advnce` → `advance`). The 2.x lifecycle commands `start`, `submit`,
`rework` and `complete`, which `tcw work advance` replaced, suggest `advance`.
Nothing is run under the suggested name. Commands that remove things are never
suggested, and a mistyped removal word (`rm`, `drop`, `delete`) gets no
suggestion at all.

A mistyped command is a usage error and exits 2. Giving `tcw work stage prompt`
a name that is not a stage is a usage error too, and the message lists the
stages.
