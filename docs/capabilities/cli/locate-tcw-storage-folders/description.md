As a user, I can print the absolute, resolved filesystem folder used by the
active taxonomy, capabilities, or work store with `tcw taxonomy path`,
`tcw capabilities path`, or `tcw work path`, and print the work inbox folder
with `tcw work inbox path`.

Each successful command emits only the path, making it safe to compose in shell
commands. The work and inbox forms follow the configured physical work-store
location.

All three commands follow a configured `<component>.path` and a declared home
repository, not only the work ones.

Where a store is declared in another repository but has not been obtained here,
there is no folder to print, so the command says so and names `tcw provision`
rather than emitting a path that does not exist. Once provisioned, it prints the
provisioned location. If the declaration itself is malformed, it names the
configuration line to fix — never "no tcw work node here", which would send me to
`tcw init` and scaffold a second, empty store beside the real one.
