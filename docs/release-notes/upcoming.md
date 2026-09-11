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
release does not remove it. Check your registered tags with `tcw work tags list`
and remove any that are two tags joined by a hyphen.

Two smaller changes worth knowing about. A command that names no tag at all,
such as `--tags ""`, is now refused rather than treated as "no tags", so a script
passing an empty variable needs to leave the option off instead. And the
abbreviation `--ta` no longer works, because it can no longer tell `--tag` and
`--tags` apart; write `--tag` in full.
