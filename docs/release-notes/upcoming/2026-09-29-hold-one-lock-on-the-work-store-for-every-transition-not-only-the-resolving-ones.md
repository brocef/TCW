## Improvements

- **Several agents can work on one store at once.**
  - Two sessions transitioning, claiming or creating different items on the
    same machine no longer pick up each other's files in a commit, or fail on
    each other's `index.lock`.
  - TCW locks the store around each command's commit, with the lock file in
    the repository's git folder, and never holds the lock across a push or
    fetch.
  - A command kept waiting says which process holds the store.
