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

There was nothing to move, and nothing you could see. That message now only
appears when your store really does hold work, including an item being started
at that very moment.
