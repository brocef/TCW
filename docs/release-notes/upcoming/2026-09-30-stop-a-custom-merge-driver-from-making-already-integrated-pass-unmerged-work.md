## Fixes

- `tcw work complete --already-integrated` could mistake an unmerged branch for a
  merged one, and delete it, in a repository that sets its own merge rules for
  some files. It no longer lets those rules decide. In such a repository, a
  branch merged by squashing that changed one of those files may now be refused;
  delete the branch yourself and run the command again.
