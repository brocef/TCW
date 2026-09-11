# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## A comma now separates tags

You can write a list of tags anywhere you could write one:

```sh
tcw work tags add cli,docs                  # register two tags
tcw work new "Login crash" --tags bug,cli   # apply two
tcw work edit my-item --untags cli,docs     # remove two
tcw work list --tags bug,cli                # show items carrying either
```

`--tags` and `--untags` are accepted anywhere `--tag` and `--untag` were, and the
two spellings mix freely.

**This also fixes something that could quietly damage a project.** Before, a
comma in a tag was not an error. `--tag cli,docs` was read as one tag named
`cli-docs`, and the error you got back told you to register `cli-docs` — advice
that, once followed, wrote that tag into your project's configuration for good.
From then on the command succeeded silently and items were tagged with something
nobody meant. Registering had no check at all, and `tcw validate` reported the
result as sound.

If a project already has a tag like `cli-docs` that was created this way, this
release does not remove it. Run `tcw work tags list` and look for a tag that is
**two of your other registered tags joined by a hyphen** — `cli-docs` where `cli`
and `docs` are both registered. That combination is the signature of the old
behaviour.

A hyphen on its own means nothing is wrong. `tech-debt` is how this system
spells a two-word tag, and removing it would leave every item carrying it
failing `tcw validate`. Only remove a tag whose two halves are themselves tags
you registered.

Two smaller changes worth knowing about. A command that names no tag at all,
such as `--tags ""`, is now refused rather than treated as "no tags", so a script
passing an empty variable needs to leave the option off instead. And the
abbreviation `--ta` no longer works, because it can no longer tell `--tag` and
`--tags` apart; write `--tag` in full.

## Moving your work store no longer refuses over an empty folder

If you have ever run `tcw work start`, your project has an empty
`docs/work/.claiming/` folder. TCW makes it while it moves an item and never
tidies it away, which is harmless — except that `tcw init --work-path` counted it
as work, and refused to move your store somewhere else:

```
tcw init: refusing to replace non-pristine …/docs/work; move existing work
manually, update work.path, then re-run init
```

There was nothing to move, and nothing you could see. An empty staging folder no
longer counts as work.

Other things in the work store still do, and rightly. A store holding items in
any status is still refused, as is one where an item is being started at that
very moment. So is one carrying `graveyard.yaml`, the record of items that were
completed or discarded — which appears the first time you resolve anything, and
is real history rather than a stray folder. If relocation is still refused and
your status folders look empty, that file is what to look for.

## A work item slug is matched as a name, not as a pattern

When a process dies partway through starting an item, the claim it was holding
is left behind and has to be recovered. TCW looked that claim up by pattern, so a
slug containing `*`, `?` or `[` could match a **different** item's claim.

**Through `tcw` itself this showed up as a confusing error.** Asking to start an
item whose name you mistyped with one of those characters paused for about a
second and then told you the item had an interrupted claim to recover — when the
item did not exist, and the claim belonged to something else. It now says there
is no such work item, straight away.

**Programs that drive TCW's Python store directly could do real damage.** There
the pattern could match another item's claim and move that item into a folder
named with the pattern, under the wrong owner, before failing. Nothing typed at
the command line could reach this, and neither could the local web app, but if
you have written scripts against `FsWorkStore` they could. If you have, look in
`docs/work/active/` for a folder whose name contains `*`, `?` or `[`: that is a
lost item. Rename it back and correct the `owner` and `started` fields in its
`state.yaml`.

## Running work items unattended

A new skill, `autonomous-work`, takes a list of work items and drives them to
completion without stopping to ask you anything. It confirms the item list and
the order once at the start, then runs.

Wherever the normal lifecycle would put a question to you — an open question in
a spec, a code review, the verification decision — it asks two independent
advisors instead, weighs their answers, decides, and writes down what it chose
and why in the item's outcome. It still stops and waits for you on anything it
should not decide alone: anything needing your credentials, anything it cannot
undo, a question about what a feature should be, and anything that spends your
money.
