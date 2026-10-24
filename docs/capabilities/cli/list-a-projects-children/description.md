As a user, I may list the projects that build on mine under `children:`, by
ID, in the committed `.tcw/tcw-config.yaml`, in my own
`.tcw/tcw-config.local.yaml`, or in both. The personal list is added after the
committed one and can only add: it lets me see a child project of my own
without changing what the team's file names. The user-wide file applies to
every project, so `children:` there is refused, naming the file; a child listed
twice, or `children: null` in the personal file, is refused too.
`TCW_NO_PERSONAL_CONFIG=1` reads only the committed list, and another
project's personal file is never read.

Every listed child must name my project among its parents; one that does not is
an error in `tcw validate`, and stops `tcw projects list`. A listed child that
is not on this machine is still listed, and `tcw validate` reports that whether
it names its parent could not be checked. `tcw projects list --json` marks a
child that only my personal file lists with `personal: true`.
