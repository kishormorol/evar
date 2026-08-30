Original path: CHANGES.md
Snapshot commit: 006b2a74d4deac01fa16e85ccc9f5810b53a7391
Original lines: 1-96

# Change Log

## Unreleased

<!-- PR authors:
     Please include the PR number in the changelog entry, not the issue number -->

- Add support for NO_COLOR environment variable to disable ANSI output (#5129)
- No spurious target version warning when runtime version is included in a
  --target-version flag (#5167)

### Highlights

<!-- Include any especially major or disruptive changes here -->

### Stable style

<!-- Changes that affect Black's stable style -->

- Stop treating a t-string in docstring position as a docstring (for example
  `t"  spam  "` as the first statement of a module, class or function). t-strings
  evaluate to `Template`, never `str`, so stripping and reindenting one changed the
  value of the template and tripped Black's AST safety check (#5287)
- Fix unparseable output for a t-string whose replacement field contains a quote (for
  example `t'\'{a["b"]}\''`). The guards that keep quote normalisation away from the
  inside of an f-string replacement field were never reached for t-strings, so the
  nested quotes were escaped and Black failed on its own output (#5265)
- Fix unparseable output for a triple-quoted string whose body ends in an already
  escaped double quote (for example `'''\'''\"'''`). Switching to `"""` escaped the
  backslash instead of the quote, leaving the closing quotes bare, so Black failed on
  its own output (#5262)
- Fix dropping the required trailing comma from a single-element tuple used as a lambda
  parameter default under `--skip-magic-trailing-comma` when a standalone comment forces
  the tuple across multiple lines; removing the comma turned the tuple into a bare
  expression and failed Black's AST safety check (#5246)
- Fix unstable formatting when an inline comment sits on optional parentheses (for
  example a parenthesized assert message or assignment RHS) (#5241)
- Fix `--skip-magic-trailing-comma` dropping the trailing comma of a one-element
  subscript (`a[x,]`) when the line is long enough to be split and contains a power
  operator (#5272)
- Fix crash when a standalone comment sits between tokens of a comprehension or lambda
  (#5144)
- Respect the magic trailing comma in a PEP 695 type parameter list containing a
  `*TypeVarTuple` or `**ParamSpec`, which previously collapsed back onto one line
  (#5244)
- Fix crash when a comment-only `# fmt: off`/`# fmt: on` block is followed by a `with`
  statement after another standalone comment (#5189)
- Fix a crash when splitting `case case if ...` match patterns at very small line
  lengths (#5147)
- Fix multiline docstring indentation when leading tabs are used inside indented
  docstrings (#5148)
- Respect `# fmt: skip` on a line that opens a bracket (e.g.
  `from x import (  # fmt: skip`) when a standalone comment is among the bracket's
  contents: the whole statement is now preserved instead of being reformatted (and
  previously crashing) (#5161)

### Preview style

<!-- Changes that affect Black's preview style -->

- Preserve two blank lines before a top-level class starting inside a `# fmt: off` block
  after an import (#5238)
- Fix unnecessary parentheses around short RHS expressions in indexed assignments like
  `x[key] = expr` (#5095)
- Parenthesize tuple expressions in `yield` statements for consistency with function
  calls and returns (#5170)
- Stop splitting between a variable and its comparator (`not in`, `==`, `is`, ...) when
  the right-hand side is a bracketed expression. Black now lets the bracket explode
  instead. This fixes the awkward break that was showing up in comprehension `if`
  clauses (#4514) as well as the same shape inside `if`, `elif`, `assert`, and
  parenthesized expressions (#5135)
- In `.pyi` stub files, enforce a blank line after a function or method that has a
  docstring-only body when another comment or statement follows it (#5158)
- Keep the parentheses around a lambda used as the iterable of a comprehension (e.g.
  `[x for x in (lambda: 0) if x]`). They were previously stripped by
  `wrap_comprehension_in`, which produced invalid code and crashed Black (#5176)
- Collapse redundant nested parentheses around a lambda or conditional expression used
  as a comprehension's iterable down to a single pair (e.g. `[x for x in ((lambda: 0))]`
  becomes `[x for x in (lambda: 0)]`). Previously the inner pair was stripped too,
  leaving the bare expression and crashing Black (#5200)

### Configuration

<!-- Changes to how Black can be configured -->

- Fix `find_project_root` returning a stale cached result when `--code` is used from
  different working directories in the same process. The CWD fallback (used when no
  `srcs` are given) is now resolved before the `lru_cache` key is computed, so each
  directory gets the correct `pyproject.toml` (#5152)
- Add validation for --line-ranges values (#5107)
- Ignore empty cache files like other malformed cache files instead of raising an
  `EOFError` (#5192)
- Reject non-string `include` and `force-exclude` values in `pyproject.toml` (#5193)
- Validate `BLACK_NUM_WORKERS` values and report invalid values as usage errors instead
  of crashing (#5211)
- Ignore permission errors when reading cache (#5258)
