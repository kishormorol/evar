Original path: CHANGES.md
Snapshot commit: 83da43a3bd43fc832fc41c5aa448338c25c7d7cb
Original lines: 160-208

  enclosed leaves for every surrounding bracket pair (#5242)
- Improve performance on lists and subscripts holding one large expression that contains
  no comparison or arithmetic sub-node (for example a long run of implicitly
  concatenated strings inside `[]`) by caching the `is_complex_subscript` subtree walk
  per node instead of re-walking the whole bracketed expression for every leaf (#5239)
- Improve performance on deeply nested expressions (such as a long `a ** b ** c ** ...`
  chain) by walking the `blib2to3` node tree iteratively in `pre_order`, `post_order`
  and `leaves` instead of recursing with `yield from`, whose per-node generator
  delegation made a full traversal quadratic in nesting depth (#5235)

### Output

<!-- Changes to Black's terminal output and error messages -->

### _Blackd_

<!-- Changes to blackd -->

### Integrations

<!-- For example, Docker, GitHub Actions, pre-commit, editors -->

### Documentation

<!-- Major changes to documentation and policies. Small docs changes
     don't need a changelog entry. -->

## Version 26.5.1

### Stable style

- Fix unstable formatting of annotated assignments whose subscript annotation contains
  an inline comment (e.g. `x: list[  # pyright: ignore[...]`) (#5130)
- Preserve inline comments (including `# type: ignore`) immediately before a
  `# fmt: skip` line, avoiding AST equivalence failures (#5139)

### Packaging

- Correct the version in the published executables (#5137)

### Documentation

- Add Neovim integration guide covering conform.nvim, ALE, and simple command approaches
  (#5124)

## Version 26.5.0

### Highlights
