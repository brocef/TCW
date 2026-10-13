As a user, I can print the absolute, resolved folder used by the current
project's taxonomy, capabilities, or work store with `tcw taxonomy path`,
`tcw capabilities path`, or `tcw work path`.

Each successful command prints only the path on standard output, making it safe
to compose in shell commands. All three follow a configured `<component>.path`
and a declared home repository. `tcw work path` also takes an item, and then
prints that item's folder or one of its stage files — see
[Read a work item](tcw://C/work/read-a-work-item).

Where a store is declared in another repository but has not been obtained here,
there is no folder to print, so the command says so on standard error, prints
nothing on standard output, and names `tcw provision` rather than printing a
path that does not exist. Once provisioned, it prints the provisioned location.
If the declaration itself is malformed, it names the configuration line to fix —
never "no TCW project here", which would send me to `tcw init` and scaffold a
second, empty store beside the real one.
