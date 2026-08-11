As a user, I can print the absolute, resolved filesystem folder used by the
active taxonomy, capabilities, or work store with `tcw taxonomy path`,
`tcw capabilities path`, or `tcw work path`, and print the work inbox folder
with `tcw work inbox path`.

Each successful command emits only the path, making it safe to compose in shell
commands. The work and inbox forms follow the configured physical work-store
location.
