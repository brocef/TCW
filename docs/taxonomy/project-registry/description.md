How TCW reads the links between projects: each project's `parents:` and
`children:` in its `.tcw/tcw-config.yaml`, by ID, and the children listed in
the active project's personal file. It finds each project's folder from its ID
(`TCW_PROJECT_<ID>`, then the manifests of the naming project and its family,
then the folders next to it and enclosing it), once per command; the manifest
entry that decides a project's folder is also the one that gives the repository
`tcw project provision` fetches it from when it is not on this machine. It
walks up through parents and down through listed children, never to a sibling;
checks that every listed child names its parent back, that there is no loop of
parents, and that no ID is found in two folders; and computes the load order.
It lists the connected projects, with how each was found, with
`tcw project list`; prints the folder of any project it can locate with
`tcw project path`; and shows how the active project is assembled, its parents,
children, load order, where its settings come from, its stores and its
overrides, with `tcw project info`.
