# Changelog

All notable changes to TCW are recorded here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions are semver.

## [Unreleased]

### Added
- Phase 1 scaffold: `tcw` Python package, `pip install -e .` console entry point,
  top-level CLI (`tcw init | taxonomy | capabilities | work`), and `tcw init` —
  the unified scaffolder for `docs/{taxonomy,capabilities,work}/` trees.
- Phase 2 taxonomy: `tcw taxonomy` (`list/add/show/rm/search/check` + bare-path
  `show`) and `FsTaxonomyStore` over `docs/taxonomy/`, with local-path `extends`
  federation and namespace reference resolution. Runtime dep `PyYAML` added.
