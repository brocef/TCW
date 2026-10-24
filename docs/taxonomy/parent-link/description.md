An entry under `parents:` in a project's `.tcw/tcw-config.yaml`: the ID of a
project this one builds on, and what that parent passes down, `inherit: all`
(the default), `none`, or a list drawn from `taxonomy`, `capabilities` and
`config`. Only the child declares it; a parent may also list the child under
`children:`, which lets work be created in the child from the parent and the
other way round.
