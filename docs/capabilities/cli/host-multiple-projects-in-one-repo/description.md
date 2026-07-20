As a user, I assign every TCW project a canonical ID and explicitly register
its direct parent and children in `tcw-config.yaml`. Registered projects may be
nested, siblings, or anywhere else on the filesystem: locators describe where
the filesystem adapter can open them, while IDs remain their stable identity.
Connections are reciprocal and fail closed when either side is missing or
inconsistent. From an enclosing project I address descendant work as
`<project-id>/<slug>` and TCW derives deeper ancestry from the registered graph
without scanning directories or git metadata.
