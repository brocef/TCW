As a user, when I type a subcommand `tcw` does not have at that level, the error
still lists every valid choice, and adds one line naming the command I probably
meant. A word that exists one level down is named in full — typing *tcw tags
list*, with `work` left out, suggests `tcw work tags list` — a common synonym
points at the real verb (`status` → `show` or `list`; `info`, `view`, `get` and
`cat` → `show`; `ls` → `list`), and a near-miss spelling points at the closest
verbs (`advnce` → `advance`). The 2.x lifecycle commands `start`, `submit`,
`rework` and `complete`, which `tcw work advance` replaced, suggest `advance`.
At most three commands are named.

**The commands TCW 4.0 moved into `tcw project`** are answered from a fixed
table before any other rule, when typed at the top level: *tcw init* is answered
with `tcw project new`, *tcw projects* (any verb) with `tcw project list`,
*tcw config* (any verb) with `tcw project config`, and *tcw provision* with
`tcw project provision`. Each answer is one line saying the old command is now
the new one; [the 3.x to 4.0 migration guide](../../../migration-guide-3.X-to-4.0.0.md) lists them.

**A synonym comes before the same word elsewhere.** When the word I typed is a
verb of another group and also a synonym whose target is valid where I typed it,
the synonym is named first: *tcw work info* suggests `tcw work show` or
`tcw project info`. Otherwise a word that is a verb somewhere else is named with
the group it belongs to, the closest group first: *tcw info* suggests
`tcw project info`, and *tcw new* suggests `tcw work new` or `tcw project new`.

Nothing is run under the suggested name. Commands that remove things are never
suggested, and a mistyped removal word (`rm`, `drop`, `delete`) gets no
suggestion at all.

A mistyped command is a usage error and exits 2. Giving `tcw work stage prompt`
a name that is not a stage is a usage error too, and the message lists the
stages.
