return {
  {
    "stevearc/oil.nvim",
    ---@module 'oil'
    ---@type oil.SetupOpts
    opts = {},
    -- Optional dependencies for file icons
    dependencies = { { "nvim-tree/nvim-web-devicons", opts = {} } },
    -- Lazy loading is not recommended as oil.nvim replaces netrw cleanly
    lazy = false,
  },
}

