The `projects:` key in a project's `.tcw/tcw-config.yaml`, which declares its
parent, children and upstream projects by ID, and how TCW reads it: finding
each project's folder from its ID (`TCW_PROJECT_<ID>`, then the manifests of
the naming project and its family, then the folders next to it and enclosing
it), once per command; checking that a parent and its children name each other
and that no ID is found in two folders; and listing the declared projects, with
how each was found, with `tcw projects list`.
