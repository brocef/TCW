## Fixes

- In the local web app (`tcw serve`), the Taxonomy and Capabilities trees now
  show each entry under the entry it names as its parent. Before, an entry
  whose parent belongs to another project, or one made with `--flat`, was shown
  at the top of the tree. When the parent is not in the list being shown (for
  example, when only this project is shown), the entry sits under a label
  naming the parent. Opening such an entry expands the tree down to it.
