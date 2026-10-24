The order in which a project's ancestors are read, ending with the project
itself: computed from every project's own order of parents by C3, the method
Python uses for classes, so that a later parent wins over an earlier one and
each project's own order is kept. When no order can keep them all, TCW uses
the depth-first order and warns, in `tcw validate` and
`tcw projects list --json`.
