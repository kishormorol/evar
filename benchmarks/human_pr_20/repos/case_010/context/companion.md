Original path: CHANGES.md
Snapshot commit: 928f50354512b3857ca07c1085076286035e4a56
Original lines: 160-208

- Improve performance on files with many `# fmt: off`/`# fmt: on` blocks by resuming the
  search for each converted block within its parent's child list from the previous
  conversion's position instead of rescanning the whole list from the start on every
  node removal (#5232)
- Improve performance on deeply nested bracketed expressions by collecting each leaf
  once in `get_leaves_inside_matching_brackets` instead of re-adding the whole span of
  enclosed leaves for every surrounding bracket pair (#5242)
- Improve performance on lists and subscripts holding one large expression that contains
  no comparison or arithmetic sub-node (for example a long run of implicitly
  concatenated strings inside `[]`) by caching the `is_complex_subscript` subtree walk
  per node instead of re-walking the whole bracketed expression for every leaf (#5239)
- Improve performance on deeply nested expressions (such as a long `a ** b ** c ** ...`
  chain) by walking the `blib2to3` node tree iteratively in `pre_order`, `post_order`
  and `leaves` instead of recursing with `yield from`, whose per-node generator
  delegation made a full traversal quadratic in nesting depth (#5235)
- Improve performance of `--preview` string merging on lines such as
  `"%s ..." % (a, b, c, ...)` by copying the leaves that surround the merged string in
  one `append_leaves` call instead of one call per leaf, which rescanned the shared
  parent's child list from the start every time (#5220)

### Output

<!-- Changes to Black's terminal output and error messages -->

### _Blackd_

<!-- Changes to blackd -->

### Integrations

<!-- For example, Docker, GitHub Actions, pre-commit, editors -->

### Documentation

<!-- Major changes to documentation and policies. Small docs changes
     don't need a changelog entry. -->

- Document `vim-python-pep8-indent`, which provides an `indentexpr` for Black-style
  insert-mode indentation (#5288)

## Version 26.5.1

### Stable style

- Fix unstable formatting of annotated assignments whose subscript annotation contains
  an inline comment (e.g. `x: list[  # pyright: ignore[...]`) (#5130)
- Preserve inline comments (including `# type: ignore`) immediately before a
  `# fmt: skip` line, avoiding AST equivalence failures (#5139)
