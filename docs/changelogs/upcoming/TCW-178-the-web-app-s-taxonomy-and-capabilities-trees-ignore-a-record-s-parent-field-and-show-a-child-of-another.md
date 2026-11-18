## Fixed

- Web client: the taxonomy and capabilities trees nest each record under the
  record its `parent` names, not only under its folder's parent. `buildPathTree`
  takes an optional `parentKeyOf`; a parent that is not listed gets label
  nodes along its key's segments, and a cycle of parent links is broken by
  putting a node caught in it back under its folder's parent. Node paths are
  unchanged, so saved expansion state still matches. New `pathTreeAncestors`
  expands the rows above a selected record along this tree, replacing
  `pathAncestors` in `navigateTo`. `CapabilityItem` now declares `parent`.
  The bundled client in `tcw/serve/dist/client` is rebuilt. (TCW-178)
