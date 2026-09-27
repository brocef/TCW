## Improvements

- **Changelog and release-note entries no longer collide between branches.**
  Instead of every change adding to one shared "upcoming" file, each change now
  writes its entries in a file of its own, named after its work item, in an
  `upcoming/` folder. When you cut a version, those files are combined into the
  version's notes, with each heading appearing once. Projects already using a
  single `upcoming.md` keep working as before; your agent will offer to switch
  them over.
