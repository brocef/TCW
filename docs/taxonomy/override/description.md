One of a project's own taxonomy entries or capabilities at the same path as one
it inherits from a parent, holding only what it changes. The two are combined
field by field: a field the override sets replaces the inherited value, one set
to `null` removes it, and one it leaves out keeps it; a list is replaced whole.
Nothing in its files marks it as an override, and its records name the object
it overrides.
