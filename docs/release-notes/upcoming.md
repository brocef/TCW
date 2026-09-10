# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## A store is found in a copy you already have

If your project keeps its board in another repository, and that repository is
already somewhere on your machine, TCW now reads the board from that copy
instead of downloading a second one.

This matters when your checkouts are not arranged the way the configuration
describes. A cloud session, a container, or a fresh laptop often clones every
repository side by side, while the configuration was written for them nested
inside one another. Before, the path in the configuration did not lead anywhere
on such a machine, so TCW downloaded its own copy of a repository sitting right
next to the one you were working in.

Tell TCW where each project is with the environment variables it already
supports, and that is now enough on its own. No symbolic links, no editing a
file that other machines read, and no machine-specific absolute paths.

The copy found this way is treated as yours. TCW reads it on whatever branch you
have it on, and never pushes to it — you push it yourself, as you would any
other folder on your disk. The downloaded copy behaved differently: it sat on
the branch named in the configuration and pushed there, so starting or
completing an item could quietly move your work onto a branch you were not on.

## A mistyped store path is no longer hidden

If you point at a folder that exists but holds no board, and your project also
says which repository the board comes from, you were told only about the second
thing. The folder you named was never mentioned, so it was easy to keep
believing it was fine and to download a second copy instead of fixing a typo.

Now both are reported, and `tcw validate` counts them as two problems rather
than one. The folder is checked whether or not the download succeeds, so you
hear about a mistake even when everything appears to work and you would
otherwise never learn you were reading the wrong copy.

A folder that simply is not there stays unmentioned. On a machine holding only
the code that is the normal situation, and saying so every time would be noise.
