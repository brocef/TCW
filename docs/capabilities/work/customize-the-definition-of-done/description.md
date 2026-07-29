As a user, I set my node's own Definition of Done in `docs/work/dod.yaml` — a plain list of strings — so the checklist `tcw work complete` prints before it accepts `--confirm` reflects what *my* project considers finished, rather than TCW's defaults.

The file **replaces** the built-in list rather than extending it. Absent or unreadable, the built-in five apply: `tests pass`, `docs synced`, `capabilities reconciled`, `reviewed`, `version offered`. Present, it is the whole checklist — so a list that omits an entry drops that check from every completion, silently and with no error. A mapping with a `checklist:` key is accepted as an alternative to a bare list.

The checklist is printed, never enforced: it prompts me and is not stored on the completed item. It reaches only the shipping path — a discard (`wontfix`, `duplicate`, `superseded`) prints no checklist at all, so lines meant to cover a non-`done` closure need somewhere else to live.
