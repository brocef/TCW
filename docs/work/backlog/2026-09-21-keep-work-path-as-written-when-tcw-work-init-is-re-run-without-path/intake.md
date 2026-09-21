# Keep work.path as written when tcw work init is re-run without --path

Re-running `tcw work init` with no `--path` reads `work.path` from
`tcw-config.yaml` through `Path(...).expanduser()` and writes `str()` of it back.
So `path: ./store` becomes `path: store`, and `path: ~/store` becomes an absolute
home-directory path in a committed file. The meaning is the same for `./`, but
`~` expanded into one person's home folder breaks the file for everyone else.
Before v2.5.1 this was buried in a full rewrite of the file. Now that config
writes change only their own lines, it shows as a one-line diff. When the path
was not given on the command line, leave the stored value untouched.

## Origin

Found by the code review of
2026-09-21-keep-comments-and-formatting-when-tcw-writes-a-key-into-tcw-config-yaml.
It predates that item. Bug.

## References

- tcw/store/fs.py: `init`'s handling of an existing `work.path`
