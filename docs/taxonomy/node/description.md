A project with a canonical ID and a `tcw-config.yaml` sentinel that owns bounded
`docs/{taxonomy,capabilities,work}/` stores. The nearest enclosing sentinel
selects the current node; cross-project relations come only from reciprocal
registered locators, never from filesystem nesting or git layout. Layout is
consulted only to resolve a relative locator to the place it was written
against — as inside a linked git worktree — never to discover a node or infer a
relation.
