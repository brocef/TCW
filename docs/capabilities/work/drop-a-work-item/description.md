As a user, I run `tcw work drop <slug> --confirm` to erase a backlog item that
should never have existed — a typo'd title, an accidental duplicate created
seconds ago. It is a hard delete: no folder survives and no record remains.
Because nothing survives it, the confirmation is required: without `--confirm`
the command tells me which item it would delete and refuses.

This is deliberately narrow. To close an item I _decided_ not to do, I complete
it with a `wontfix`, `duplicate`, or `superseded` resolution, which files it
under `discarded/` and keeps the decision on record. Drop is for mistakes;
discard is for decisions.
