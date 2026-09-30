As a user, when I type a subcommand `tcw` does not have at that level, the error
still lists every valid choice, and adds one line naming the command I probably
meant. A word that exists one level down is named in full — typing *tcw tracker
status*, with `work` left out, suggests `tcw work tracker show` — a common
synonym points at the real verb (`status` → `show` or `list`, `ls` → `list`),
and a near-miss spelling points at the closest verbs (`strat` → `start`).
Nothing is run under the suggested name. Commands that remove things are never
suggested, and a mistyped removal word gets no suggestion at all.

Giving `tcw work stage gate` or `prompt` the name of an artifact instead of a
stage says which stage writes it — `refined-outcome` → the `verify` stage — and
giving it a transition such as `start` says to run `tcw work start` instead.
