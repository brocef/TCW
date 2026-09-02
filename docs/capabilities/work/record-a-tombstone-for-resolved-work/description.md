As a user, I run `tcw work tombstone add <slug>` to record that a slug named a
work item this project once held and has since finished with — so that
references to it resolve instead of reading like misspellings.

I need this because resolving an item takes its documents out of the tracked
tree, and anything resolved before this existed left no record behind at all.
Without a way to record a slug after the fact, every reference written before
today keeps reporting a problem forever. Recording one is how an existing
project starts benefiting; a project starting fresh never needs the command,
because completing and discarding record themselves.

I may pass `--resolution done|wontfix|duplicate|superseded` and `--resolved
<ISO date>`, and I may omit either. Omitting is the honest answer when nobody
kept the detail: the record's job is to say the slug existed, and inventing a
resolution or a date would be worse than admitting it is unknown. The date
defaults to today, which reads as "known resolved by then".

The tool refuses to record a slug that is currently a live work item — a
project cannot both be holding an item and be finished with it — and it commits
what it writes, the same way a status change commits itself, because a record
that never leaves my machine helps nobody else who clones the project.
