Original path: docs/integrations/editors.md
Snapshot commit: 83da43a3bd43fc832fc41c5aa448338c25c7d7cb
Original lines: 307-417


On first run, the plugin creates its own virtualenv using the right Python version and
automatically installs _Black_. You can upgrade it later by calling `:BlackUpgrade` and
restarting Vim.

If you need to do anything special to make your virtualenv work and install _Black_ (for
example you want to run a version from main), create a virtualenv manually and point
`g:black_virtualenv` to it. The plugin will use it.

If you would prefer to use the system installation of _Black_ rather than a virtualenv,
then add this to your vimrc:

```vim
let g:black_use_virtualenv = 0
```

Note that the `:BlackUpgrade` command is only usable and useful with a virtualenv, so
when the virtualenv is not in use, `:BlackUpgrade` is disabled. If you need to upgrade
the system installation of _Black_, then use your system package manager or pip--
whatever tool you used to install _Black_ originally.

To run _Black_ on save, add the following lines to `.vimrc` or `init.vim`:

```vim
augroup black_on_save
  autocmd!
  autocmd BufWritePre *.py Black
augroup end
```

To run _Black_ on a key press (e.g. F9 below), add this:

```vim
nnoremap <F9> :Black<CR>
```

### With ALE

1. Install [`ale`](https://github.com/dense-analysis/ale)

1. Install `black`

1. Add this to your vimrc:

   ```vim
   let g:ale_fixers = {}
   let g:ale_fixers.python = ['black']
   ```

### Vim indentation plugin

For insert-mode indentation that follows the same hanging-bracket style as _Black_, you
can also use the
[`vim-python-pep8-indent`](https://github.com/Vimjas/vim-python-pep8-indent) plugin. It
provides Vim's `indentexpr`; _Black_ remains responsible for formatting the file. For
example, with [vim-plug](https://junegunn.github.io/vim-plug/):

```vim
Plug 'Vimjas/vim-python-pep8-indent'
```

With Vundle, use:

```vim
Plugin 'Vimjas/vim-python-pep8-indent'
```

## Neovim

### Via conform.nvim

[conform.nvim](https://github.com/stevearc/conform.nvim) is a lightweight formatter
plugin for Neovim. It supports _Black_ out of the box as long as `black` is available in
your `PATH`.

1. Install `black` (e.g. `pip install black` or `pipx install black`)

1. Install `conform.nvim` using your plugin manager and add the following to your Neovim
   configuration:

   ```lua
   require("conform").setup({
     formatters_by_ft = {
       python = { "black" },
     },
   })
   ```

1. To format on save, add:

   ```lua
   require("conform").setup({
     formatters_by_ft = {
       python = { "black" },
     },
     format_on_save = {
       timeout_ms = 500,
       lsp_format = "fallback",
     },
   })
   ```

### With ALE

[ALE](https://github.com/dense-analysis/ale) supports both Vim and Neovim. See the
[Vim section](#with-ale) above for setup instructions — the same configuration works for
Neovim.

### Simple command

You can invoke _Black_ on the current file directly from Neovim without any plugins:
